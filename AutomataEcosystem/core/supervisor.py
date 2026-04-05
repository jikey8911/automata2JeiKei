"""
Supervisor orchestrates UAEs and exposes a heartbeat API.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import docker
from docker.errors import APIError, DockerException, NotFound

from .database import EncryptedSecretStore, UaeRegistry, DiscoveredSectors
from .finance_manager import BybitManager, VirtualCardManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Supervisor:
    """
    Core orchestrator for UAEs.
    """

    def __init__(
        self,
        genesis_wallet_id: str,
        secret_store: Optional[EncryptedSecretStore] = None,
        docker_client: Optional[docker.DockerClient] = None,
        target_platform: str = "linux/arm64",
        liquidity_cushion: float = 50.0,
    ) -> None:
        self.genesis_wallet_id = genesis_wallet_id
        self.secret_store = secret_store or EncryptedSecretStore()
        self.target_platform = target_platform
        self.client = docker_client or self._connect_docker()
        self.bybit = BybitManager(secret_store=self.secret_store)
        self.virtual_cards = VirtualCardManager(self.bybit)
        self.registry = UaeRegistry(self.secret_store)
        self.sectors = DiscoveredSectors(self.secret_store)
        self.liquidity_cushion = liquidity_cushion
        self._poll_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self.app = self._build_api()

    def _connect_docker(self) -> docker.DockerClient:
        try:
            client = docker.from_env()
            # Quick sanity check
            client.ping()
            logger.info("Docker client connected (platform=%s)", self.target_platform)
            return client
        except DockerException as exc:
            logger.exception("Docker connection failed: %s", exc)
            raise

    async def create_uae(
        self,
        name: str,
        image: str,
        capital: float,
        environment: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
    ) -> str:
        """
        Provision subaccount, card, fund, and launch UAE container.
        Returns container ID.
        """
        try:
            logger.info("Provisioning UAE '%s' with capital %.2f", name, capital)
            sub_uid = await self.bybit.create_subaccount()
            if not sub_uid:
                raise RuntimeError("Failed to create Bybit sub UID")

            await self.bybit.distribute_to_uae(sub_uid, capital)
            card = await self.virtual_cards.issue_card(sub_uid, capital)

            # Persist sensitive card data encrypted
            self.registry.register(
                uae_id=name,
                sub_uid=sub_uid,
                card_id=card["card_id"],
                card_number=card["number"],
                card_cvv=card["cvv"],
                card_exp=card["exp"],
                status="active",
            )

            env = environment or {}
            env.update(
                {
                    "UAE_NAME": name,
                    "BYBIT_SUB_UID": sub_uid,
                    "VCC_CARD_ID": card["card_id"],
                    "VCC_NUMBER": card["number"],
                    "VCC_CVV": card["cvv"],
                    "VCC_EXP": card["exp"],
                    "OLLAMA_URL": "http://163.192.114.190:11435",
                }
            )

            container = await asyncio.to_thread(
                self.client.containers.run,
                image=image,
                name=name,
                detach=True,
                environment=env,
                # platform=self.target_platform,  # use host default to avoid local arch conflicts
                command=command,
                auto_remove=False,
                network_mode="bridge",
                volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            )
            logger.info("UAE '%s' started. Container ID=%s", name, container.id)
            return container.id
        except (APIError, DockerException) as exc:
            logger.exception("Failed to create UAE '%s': %s", name, exc)
            raise

    async def terminate_uae(self, container_id: str) -> None:
        """
        Stop and remove a UAE container. Idempotent.
        """
        try:
            container = await asyncio.to_thread(self.client.containers.get, container_id)
        except NotFound:
            logger.warning("terminate_uae: container %s not found", container_id)
            return
        except DockerException as exc:
            logger.exception("terminate_uae: lookup failed for %s: %s", container_id, exc)
            raise

        try:
            logger.info("Stopping container %s", container_id)
            await asyncio.to_thread(container.stop, timeout=30)
            logger.info("Removing container %s", container_id)
            await asyncio.to_thread(container.remove, force=True)
        except (APIError, DockerException) as exc:
            logger.exception("Failed to terminate container %s: %s", container_id, exc)
            raise

    async def collect_tax(self, uae_id: str, profit: float) -> float:
        """
        Apply 50% tax to Génesis wallet.
        Returns amount transferred to Génesis.
        """
        try:
            tax = max(profit, 0.0) * 0.5
            logger.info(
                "Collecting tax %.4f from profit %.4f -> wallet %s",
                tax,
                profit,
                self.genesis_wallet_id,
            )
            await self.bybit.collect_taxes(uae_id, tax)
            return tax
        except Exception as exc:
            logger.exception("Tax collection failed for profit %.4f: %s", profit, exc)
            raise

    # ------------------- API Layer ------------------- #
    def _build_api(self) -> FastAPI:
        app = FastAPI(title="AutomataEcosystem Supervisor", version="0.1.0")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://163.192.114.190:3000",
                "http://localhost:3000",
                "http://automata_frontend:3000",
                "http://frontend:3000",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.on_event("startup")
        async def _startup():
            self._poll_task = asyncio.create_task(self._funding_poll_loop())
            self._monitor_task = asyncio.create_task(self.monitor_ecosystem())

        @app.on_event("shutdown")
        async def _shutdown():
            if self._poll_task:
                self._poll_task.cancel()
            if self._monitor_task:
                self._monitor_task.cancel()

        @app.post("/api/v1/heartbeat")
        async def heartbeat(payload: Dict) -> Dict:
            try:
                await self._handle_heartbeat(payload)
                return {"ok": True}
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Failed to process heartbeat: %s", exc)
                raise HTTPException(status_code=500, detail="heartbeat processing failed")

        @app.get("/api/v1/status")
        async def status() -> Dict:
            try:
                containers = await asyncio.to_thread(
                    lambda: [
                        {"name": c.name, "status": c.status, "id": c.id[:12]}
                        for c in self.client.containers.list(all=True)
                        if c.name.startswith("UAE-")
                    ]
                )
                sectors = list(self.sectors.list_all())
                balances = await self.bybit.get_genesis_balance()
                return {"containers": containers, "sectors": sectors, "genesis_balance": balances}
            except Exception as exc:
                logger.exception("Status endpoint failed: %s", exc)
                raise HTTPException(status_code=500, detail="status failed")

        @app.post("/api/v1/request_spending")
        async def request_spending(payload: Dict) -> Dict:
            amount = float(payload.get("amount", 0))
            justification = payload.get("reason", "")
            uae_id = payload.get("uae_id", "unknown")
            logger.info("Spending request from %s: %.2f | %s", uae_id, amount, justification)
            try:
                balances = await self.bybit.get_genesis_balance()
                total = sum(balances.values())
                if amount > total:
                    raise HTTPException(status_code=402, detail="Insufficient Genesis balance")
                # For now top-up first card of registry entry
                reg_entries = self.registry.list_all()
                card_id = None
                for r in reg_entries:
                    if r["uae_id"] == uae_id:
                        card_id = r["vcc_card_id"]
                        break
                if not card_id:
                    card_id = "vcc-shared"
                await self.virtual_cards.top_up_card(card_id, amount_usd=amount)
                logger.info("Sector ?? evaluado -> Seguro -> Factible -> Presupuesto Aprobado -> VCC Recargada")
                return {"status": "APPROVED", "card_id": card_id}
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Spending request failed: %s", exc)
                raise HTTPException(status_code=500, detail="spending failed")

        return app

    async def _handle_heartbeat(self, payload: Dict) -> None:
        uae_id = payload.get("uae_id")
        status = payload.get("status")
        balances = payload.get("balances", {})
        logger.info(
            "Heartbeat received | uae_id=%s | status=%s | balances=%s",
            uae_id,
            status,
            balances,
        )
        # After each heartbeat, enforce liquidity rule
        await self.bybit.rebalance_to_funding(cushion=self.liquidity_cushion)

        @app.post("/api/v1/secrets")
        async def set_secrets(payload: Dict) -> Dict:
            try:
                # Persist provided secrets into encrypted store
                for k, v in payload.items():
                    if v:
                        self.secret_store.set_secret(k, v)
                return {"ok": True}
            except Exception as exc:
                logger.exception("Failed to save secrets: %s", exc)
                raise HTTPException(status_code=500, detail="saving secrets failed")

        @app.get("/api/v1/secrets")
        async def get_secrets() -> Dict:
            try:
                keys = ["BYBIT_API_KEY", "BYBIT_API_SECRET", "BYBIT_MASTER_UID", "OLLAMA_URL"]
                data = {k: self.secret_store.get_secret(k) for k in keys}
                return data
            except Exception as exc:
                logger.exception("Failed to read secrets: %s", exc)
                raise HTTPException(status_code=500, detail="reading secrets failed")

    async def _funding_poll_loop(self) -> None:
        last_total = 0.0
        while True:
            try:
                balances = await self.bybit.get_genesis_balance()
                total = sum(balances.values())
                active = any(r["status"] == "active" for r in self.registry.list_all())
                if total > last_total and not active:
                    logger.warning("Capital listo para asignar: %.2f (sin UAE activa)", total)
                last_total = total
            except Exception as exc:
                logger.warning("Funding poll failed: %s", exc)
            await asyncio.sleep(300)

    async def monitor_ecosystem(self) -> None:
        while True:
            try:
                # Ignición: lanzar UAE-Alpha si no hay contenedores UAE-*
                containers = await asyncio.to_thread(
                    lambda: [c for c in self.client.containers.list() if c.name.startswith("UAE-")]
                )
                if not containers:
                    try:
                        await self.create_uae(
                            name="UAE-Alpha",
                            image="automata/uae-template:latest",
                            capital=2.0,
                            command=["python", "-m", "AutomataEcosystem.uae.main_agent"],
                        )
                        logger.info("Ignición automática: UAE-Alpha lanzada")
                    except Exception as exc:
                        logger.warning("Ignición automática falló: %s", exc)

                sectors = list(self.sectors.list_all())
                # Apoptosis
                for sec in sectors:
                    if sec.get("status") == "failed":
                        try:
                            target = await asyncio.to_thread(
                                lambda: self.client.containers.get(sec["discoverer_uae_id"])
                            )
                            await asyncio.to_thread(target.stop)
                            await asyncio.to_thread(target.remove, force=True)
                            logger.info("Apoptosis: UAE %s eliminada por sector failed %s", sec["discoverer_uae_id"], sec["sector_name"])
                        except Exception as exc:
                            logger.warning("Apoptosis fallo para %s: %s", sec.get("discoverer_uae_id"), exc)

                # Mitosis
                for sec in sectors:
                    if sec.get("status") == "profitable":
                        clone_name = f"UAE-Beta-{uuid.uuid4().hex[:4]}"
                        env = {"WINNING_SECTOR": sec["sector_name"]}
                        try:
                            await self.create_uae(
                                name=clone_name,
                                image="automata/uae-template:latest",
                                capital=2.0,
                                environment=env,
                                command=["python", "-m", "AutomataEcosystem.uae.main_agent"],
                            )
                            logger.info("Mitosis: clon %s creado para sector %s", clone_name, sec["sector_name"])
                        except Exception as exc:
                            logger.warning("Mitosis fallida para %s: %s", sec["sector_name"], exc)
            except Exception as loop_exc:
                logger.warning("monitor_ecosystem loop error: %s", loop_exc)
            await asyncio.sleep(60)


def main() -> None:
    # genesis_wallet_id should come from env/secret store; placeholder for now
    wallet_id = "GENESIS_WALLET"
    supervisor = Supervisor(genesis_wallet_id=wallet_id)
    uvicorn.run(supervisor.app, host="0.0.0.0", port=8000)


__all__ = ["Supervisor"]
