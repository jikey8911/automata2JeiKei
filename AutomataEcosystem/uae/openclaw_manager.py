"""
OpenClaw Manager
----------------
Runs inside each UAE container to orchestrate Workers (sub-processes/containers).
LLM-driven strategy loading is intentionally omitted at this stage; only the control
skeleton and safety plumbing are provided.
"""

from __future__ import annotations

import logging
import subprocess
import shutil
from typing import Optional, List

import docker
from docker.errors import DockerException, APIError, NotFound

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class OpenClawManager:
    def __init__(self, docker_client: Optional[docker.DockerClient] = None, target_platform: str = "linux/arm64"):
        self.client = docker_client or self._connect_docker()
        self.target_platform = target_platform

    def _connect_docker(self) -> docker.DockerClient:
        try:
            client = docker.from_env()
            client.ping()
            logger.info("OpenClaw connected to Docker daemon")
            return client
        except DockerException as exc:
            logger.exception("Docker connection error in OpenClaw: %s", exc)
            raise

    def spawn_worker(self, name: str, image: str, environment: Optional[dict] = None, command: Optional[str] = None) -> str:
        """
        Start a new worker container. Actual skill loading is handled elsewhere.
        """
        try:
            env = environment or {}
            env.setdefault("WORKER_NAME", name)
            container = self.client.containers.run(
                image=image,
                name=name,
                detach=True,
                environment=env,
                # platform=self.target_platform, # removed for stability in local dev
                command=command,
                auto_remove=False,
                network_mode="bridge",
            )
            logger.info("Worker '%s' spawned (id=%s)", name, container.id)
            return container.id
        except (APIError, DockerException) as exc:
            logger.exception("Failed to spawn worker '%s': %s", name, exc)
            raise

    def spawn_strategy_agent(self, strategy_id: str, code: str, environment: dict) -> str:
        """
        Spawns a specialized agent (worker) to run a specific strategy code.
        It uses a base python image and injects the code as a command.
        """
        try:
            name = f"worker-{strategy_id[:8]}"
            # We wrap the code to ensure it has the necessary imports and error handling
            full_script = (
                "import os, sys, json, asyncio, logging\n"
                "logging.basicConfig(level=logging.INFO)\n"
                "logger = logging.getLogger('worker')\n"
                "async def main():\n"
                "    try:\n"
                "        logger.info('Worker starting strategy...')\n"
                "        # --- START CORE STRATEGY ---\n"
                f"{code}\n"
                "        # --- END CORE STRATEGY ---\n"
                "    except Exception as e:\n"
                "        logger.error(f'Worker failed: {e}')\n\n"
                "if __name__ == '__main__':\n"
                "    asyncio.run(main())"
            )
            
            # Command to run the script via python -c
            command = ["python", "-c", full_script]
            
            return self.spawn_worker(
                name=name,
                image="python:3.11-slim",
                environment=environment,
                command=command
            )
        except Exception as exc:
            logger.exception("Failed to spawn strategy agent %s: %s", strategy_id, exc)
            raise

    def clone_worker(self, source_container_id: str, new_name: str) -> str:
        """
        Clone a worker container from an existing one (commit -> run).
        """
        try:
            source = self.client.containers.get(source_container_id)
        except NotFound:
            logger.error("clone_worker: source container %s not found", source_container_id)
            raise
        except DockerException as exc:
            logger.exception("clone_worker: lookup failed: %s", exc)
            raise

        try:
            image = source.commit(repository=f"clone/{new_name}", tag="latest")
            logger.info("Committed worker %s to image %s", source_container_id, image.id)
            new_container = self.client.containers.run(
                image=image.id,
                name=new_name,
                detach=True,
                platform=self.target_platform,
                auto_remove=False,
                network_mode="bridge",
            )
            logger.info("Cloned worker '%s' -> '%s' (id=%s)", source_container_id, new_name, new_container.id)
            return new_container.id
        except (APIError, DockerException) as exc:
            logger.exception("Failed to clone worker %s: %s", source_container_id, exc)
            raise

    def kill_worker(self, container_id: str) -> None:
        """
        Stop and remove a worker container. Idempotent.
        """
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            logger.warning("kill_worker: container %s not found", container_id)
            return
        except DockerException as exc:
            logger.exception("kill_worker: lookup failed for %s: %s", container_id, exc)
            raise

        try:
            logger.info("Stopping worker %s", container_id)
            container.stop(timeout=20)
            logger.info("Removing worker %s", container_id)
            container.remove(force=True)
        except (APIError, DockerException) as exc:
            logger.exception("Failed to kill worker %s: %s", container_id, exc)
            raise

    # -------- Skill runtime helpers -------- #
    def ensure_brew(self) -> bool:
        """
        Best-effort check/install of Homebrew (Linuxbrew). Many base images
        won't have brew; we log and continue instead of raising hard errors.
        """
        brew_path = shutil.which("brew")
        if brew_path:
            logger.info("brew found at %s", brew_path)
            return True

        logger.warning("brew not found in this container. Skills requiring brew may fail. Skipping install.")
        return False

    def install_with_brew(self, packages: List[str]) -> None:
        """
        Install skill dependencies with brew if available.
        """
        if not packages:
            return
        if not self.ensure_brew():
            logger.warning("install_with_brew skipped; brew unavailable.")
            return
        for pkg in packages:
            try:
                logger.info("Installing skill dependency via brew: %s", pkg)
                subprocess.run(["brew", "install", pkg], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc:
                logger.warning("brew install failed for %s: %s", pkg, exc)


__all__ = ["OpenClawManager"]
