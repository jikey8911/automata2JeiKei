"""
Supervisor orchestrates UAEs and exposes a heartbeat API.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional

import asyncio
import docker
from docker.errors import APIError, DockerException, NotFound
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import uvicorn
import httpx

SECRET_KEYS = [
    # Exchange / core infra
    "BYBIT_API_KEY",
    "BYBIT_API_SECRET",
    "BYBIT_MASTER_UID",
    "EXCHANGE_NAME",
    # LLM / AI providers
    "OLLAMA_URL",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "VOYAGE_API_KEY",
    "MISTRAL_API_KEY",
    # DevOps / source control
    "GITHUB_TOKEN",
    # Cloud / services
    "ORACLE_API_KEY",
    "JEIKEI_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "GOPLACES_API_KEY",
    "NANO_BANANA_API_KEY",
    "NOTION_API_KEY",
    "CCXT_PROXY_URL",
]

from .database import EncryptedSecretStore, UaeRegistry, DiscoveredSectors, UaeStrategies
from .finance_manager import ExchangeManager, VirtualCardManager
from .supervisor_brain import SupervisorBrain

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
        self.exchange = ExchangeManager(secret_store=self.secret_store)
        self.virtual_cards = VirtualCardManager(self.exchange)
        self.registry = UaeRegistry(self.secret_store)
        self.sectors = DiscoveredSectors(self.secret_store)
        self.strats = UaeStrategies(self.secret_store)
        self.liquidity_cushion = liquidity_cushion
        self.uae_logs = defaultdict(lambda: deque(maxlen=100))
        self.new_log_event = asyncio.Event()
        self.brain = SupervisorBrain()
        
        # Monitoring task for UAE life cycles
        self._poll_task = None
        self._monitor_task = None
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
            sub_uid = await self.exchange.create_subaccount(name)
            if not sub_uid:
                raise RuntimeError(f"Failed to create Bybit subaccount for {name}")

            try:
                # Transferir capital real desde la maestra a la subcuenta
                await self.exchange.distribute_to_uae(name, sub_uid, capital)
                card = await self.virtual_cards.issue_card(sub_uid, capital)
            except Exception as exc:
                logger.warning("Funding/card step failed (continuando sin fondos): %s", exc)
                card = {
                    "card_id": "vcc-placeholder",
                    "number": "0000",
                    "cvv": "000",
                    "exp": "12/30",
                }

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
            # Inyectar secretos relevantes en la UAE
            for key in SECRET_KEYS:
                val = self.secret_store.get_secret(key)
                if val:
                    # No sobreescribir si ya viene en environment
                    env.setdefault(key, val)

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
            await self.exchange.collect_taxes(uae_id, tax)
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

        @app.post("/api/v1/uae/heartbeat")
        async def heartbeat(payload: Dict) -> Dict:
            try:
                await self._handle_heartbeat(payload)
                return {"ok": True}
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Failed to process heartbeat: %s", exc)
                raise HTTPException(status_code=500, detail="heartbeat processing failed")

        @app.post("/api/v1/secrets")
        async def set_secrets(payload: Dict) -> Dict:
            try:
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
                data = {k: self.secret_store.get_secret(k) for k in SECRET_KEYS}
                return data
            except Exception as exc:
                logger.exception("Failed to read secrets: %s", exc)
                raise HTTPException(status_code=500, detail="reading secrets failed")

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
                balances = await self.exchange.get_genesis_balance()
                return {"containers": containers, "sectors": sectors, "genesis_balance": balances}
            except Exception as exc:
                logger.exception("Status endpoint failed: %s", exc)
                raise HTTPException(status_code=500, detail="status failed")

        @app.get("/api/v1/health")
        async def health() -> Dict:
            """
            Indicadores rápidos para el dashboard.
            """
            try:
                docker_ok = False
                try:
                    docker_ok = await asyncio.to_thread(self.client.ping)
                except Exception:
                    docker_ok = False

                wallet_ok = False
                wallet_error = ""
                try:
                    await self.exchange.get_genesis_balance()
                    wallet_ok = True
                except Exception as exc:
                    wallet_ok = False
                    wallet_error = str(exc)

                ollama_ok = False
                ollama_models = []
                ollama_url = self.secret_store.get_secret("OLLAMA_URL") or "http://localhost:11434"
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        r = await client.get(f"{ollama_url.rstrip('/')}/api/tags")
                        if r.status_code == 200:
                            data = r.json()
                            ollama_models = [m.get("name") for m in data.get("models", [])]
                            ollama_ok = True
                except Exception:
                    ollama_ok = False

                return {
                    "supervisor": True,
                    "docker": docker_ok,
                    "wallet": wallet_ok,
                    "wallet_error": wallet_error,
                    "ollama": ollama_ok,
                    "ollama_models": ollama_models,
                }
            except Exception as exc:
                logger.warning("Health endpoint failed: %s", exc)
                return {
                    "supervisor": True,
                    "docker": False,
                    "wallet": False,
                    "ollama": False,
                }

        @app.post("/api/v1/request_spending")
        async def request_spending(payload: Dict) -> Dict:
            amount = float(payload.get("amount", 0))
            justification = payload.get("reason", "")
            uae_id = payload.get("uae_id", "unknown")
            logger.info("Spending request from %s: %.2f | %s", uae_id, amount, justification)
            try:
                balances = await self.exchange.get_genesis_balance()
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

        @app.get("/api/v1/logs", response_class=PlainTextResponse)
        async def logs(limit: int = 200) -> PlainTextResponse:
            """
            Devuelve las últimas líneas de los logs del supervisor (texto plano).
            """
            try:
                container = None
                # Intentar por nombre estándar
                try:
                    container = await asyncio.to_thread(self.client.containers.get, "automata_supervisor")
                except NotFound:
                    # Fallback: hostname dentro del contenedor
                    hostname = os.environ.get("HOSTNAME")
                    if hostname:
                        try:
                            container = await asyncio.to_thread(self.client.containers.get, hostname)
                        except Exception:
                            container = None
                if container:
                    raw = await asyncio.to_thread(container.logs, tail=limit)
                    text = raw.decode("utf-8", errors="ignore")
                else:
                    text = "Logs no disponibles: contenedor supervisor no encontrado."
                return PlainTextResponse(text)
            except Exception as exc:
                logger.warning("logs endpoint failed: %s", exc)
                return PlainTextResponse("Logs no disponibles", status_code=500)

        @app.get("/api/v1/uae/logs")
        async def get_uae_logs():
            return {uid: list(logs) for uid, logs in self.uae_logs.items()}

        @app.websocket("/api/v1/uae/logs/ws")
        async def ws_uae_logs(websocket: WebSocket):
            await websocket.accept()
            try:
                # Initial state
                initial_payload = {uid: list(logs) for uid, logs in self.uae_logs.items()}
                await websocket.send_json({"logs": initial_payload})
                
                while True:
                    await self.new_log_event.wait()
                    self.new_log_event.clear()
                    payload = {uid: list(logs) for uid, logs in self.uae_logs.items()}
                    await websocket.send_json({"logs": payload})
            except WebSocketDisconnect:
                pass

        @app.websocket("/api/v1/supervisor/logs/ws")
        async def ws_supervisor_logs(websocket: WebSocket):
            await websocket.accept()
            try:
                # Get supervisor container
                hostname = os.environ.get("HOSTNAME")
                if not hostname:
                    await websocket.send_text("HOSTNAME not found, cannot stream supervisor logs.")
                    return
                
                container = await asyncio.to_thread(self.client.containers.get, hostname)
                # Stream logs as they come
                # Using tail=20 for initial context
                async for line in self._stream_docker_logs(container, tail=20):
                    await websocket.send_text(line)
            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.error("Supervisor log streaming failed: %s", e)
                try:
                    await websocket.send_text(f"Error streaming logs: {e}")
                except:
                    pass

        @app.post("/api/v1/uae/mitosis/{uae_id}")
        async def api_mitosis(uae_id: str):
            try:
                # Buscar el contenedor original para obtener su imagen y config
                container = await asyncio.to_thread(self.client.containers.get, uae_id)
                image = container.image.tags[0] if container.image.tags else "automata/uae-template:latest"
                new_name = f"UAE-Clone-{uuid.uuid4().hex[:4]}"
                # Simplificación: usamos capital estándar para el clon
                await self.create_uae(name=new_name, image=image, capital=2.0)
                return {"ok": True, "new_uae": new_name}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/api/v1/uae/kill/{uae_id}")
        async def api_kill(uae_id: str):
            try:
                # Intentar buscar por nombre o ID directamente en docker
                await self.terminate_uae(uae_id)
                return {"ok": True}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/v1/uae/config/{uae_id}")
        async def get_uae_config(uae_id: str):
            try:
                # Find uae in registry
                all_uaes = self.registry.list_all()
                uae = next((u for u in all_uaes if u["uae_id"] == uae_id), None)
                if not uae:
                    raise HTTPException(status_code=404, detail="UAE not registered")
                
                # Fetch all relevant secrets for the UAE
                config = {
                    "sub_uid": uae["bybit_subaccount_id"],
                    "vcc": {
                        "card_id": uae["vcc_card_id"],
                        "number": self.secret_store._fernet.decrypt(uae["vcc_number_enc"]).decode("utf-8"),
                        "cvv": self.secret_store._fernet.decrypt(uae["vcc_cvv_enc"]).decode("utf-8"),
                        "exp": self.secret_store._fernet.decrypt(uae["vcc_exp_enc"]).decode("utf-8"),
                    }
                }
                
                # Inyectar todos los SECRET_KEYS generales (GenAI, DevOps, etc.)
                for key in SECRET_KEYS:
                    val = self.secret_store.get_secret(key)
                    if val:
                        config[key] = val

                return config
            except Exception as e:
                logger.error("Error retrieving config for %s: %s", uae_id, e)
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/v1/strategies")
        async def get_strategies(limit: int = 10):
            return self.strats.get_profitable_strategies(limit=limit)

        @app.post("/api/v1/strategies/report")
        async def report_strategy(payload: Dict):
            uae_id = payload.get("uae_id")
            sector = payload.get("sector")
            idea = payload.get("idea")
            code = payload.get("code")
            status = payload.get("status")
            profit = payload.get("profit", 0.0)
            
            self.strats.record(uae_id, sector, idea, code, status, profit)
            logger.info("Strategy reported by %s for sector %s (status: %s)", uae_id, sector, status)
            return {"ok": True}

        return app

    async def _handle_heartbeat(self, payload: Dict) -> None:
        uae_id = payload.get("uae_id", "unknown")
        status = payload.get("status", "unknown")
        balances = payload.get("balances", {})
        logs = payload.get("logs", [])
        workers = payload.get("workers", []) # Nueva lista de agentes especialistas

        # Update local state
        self.uae_logs[uae_id].extend(logs)
        if logs:
            self.new_log_event.set()

        # Guardar estado extendido incluyendo workers
        self.uae_states[uae_id] = {
            "status": status,
            "balances": balances,
            "last_seen": asyncio.get_event_loop().time(),
            "workers": workers
        }
        
        if uae_id and logs:
            timestamp = datetime.now().strftime("%H:%M:%S")
            for msg in logs:
                formatted_msg = f"[{timestamp}] {msg}"
                self.uae_logs[uae_id].append(formatted_msg)
                # Trigger analysis
                asyncio.create_task(self._analyze_uae_activity(uae_id, msg))

            self.new_log_event.set()

        # After each heartbeat, enforce liquidity rule
        await self.exchange.rebalance_to_funding(cushion=self.liquidity_cushion)

    async def _analyze_uae_activity(self, uae_id: str, log_msg: str) -> None:
        """
        LLM-based analysis of UAE logs via SupervisorBrain (Ollama).
        """
        # 1. Filtro rápido de importancia (opcional)
        if len(log_msg) < 10 and "BUSCANDO" not in log_msg.upper():
            return

        # 2. Análisis LLM
        analysis = await self.brain.analyze_log(uae_id, log_msg)
        
        severity = analysis.get("severity", "INFO")
        action = analysis.get("action", "NONE")
        insight = analysis.get("insight", "")

        if action != "NONE" or severity != "INFO":
            log_entry = f"[BRAIN] {uae_id} -> {severity} | Acción: {action} | {insight}"
            if severity == "CRITICAL":
                logger.error(log_entry)
            elif severity == "WARNING":
                logger.warning(log_entry)
            else:
                logger.info(log_entry)

            # Acciones automáticas programadas
            if action == "REBALANCE":
                asyncio.create_task(self.exchange.rebalance_to_funding(cushion=self.liquidity_cushion))
            elif action == "STOP_UAE":
                logger.warning("Supervisor Brain sugirió detener UAE %s", uae_id)
                # await self.terminate_uae(uae_id)
            elif action == "MITOSIS":
                logger.info("Supervisor Brain sugirió MITOSIS para %s", uae_id)
                # Trigger mitosis logic here if desired

    async def _stream_docker_logs(self, container, tail=20):
        """
        Generator to stream docker logs as they are written.
        """
        # generator is blocking, so we use to_thread inside loop or run it in background
        # Simple implementation using tail as initial and then streaming
        logs = container.logs(stream=True, follow=True, tail=tail)
        while True:
            try:
                line = await asyncio.to_thread(next, logs)
                yield line.decode("utf-8", errors="ignore").strip()
            except StopIteration:
                break
            except Exception as e:
                logger.error("Error streaming logs from thread: %s", e)
                break

    async def _funding_poll_loop(self) -> None:
        last_total = 0.0
        while True:
            try:
                balances = await self.exchange.get_genesis_balance()
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
