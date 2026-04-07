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
from pathlib import Path

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
    "OPENCLAW_GATEWAY_TOKEN",
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
        self._ensure_network()
        self.exchange = ExchangeManager(secret_store=self.secret_store)
        self.virtual_cards = VirtualCardManager(self.exchange)
        self.registry = UaeRegistry(self.secret_store)
        self.sectors = DiscoveredSectors(self.secret_store)
        self.strats = UaeStrategies(self.secret_store)
        self.liquidity_cushion = liquidity_cushion
        # Por defecto, apuntamos al host Ollama provisto
        self.ollama_url = self.secret_store.get_secret("OLLAMA_URL") or os.getenv("OLLAMA_URL", "http://163.192.114.190:11435")
        self.uae_logs = defaultdict(lambda: deque(maxlen=100))
        self.uae_states = {}
        self.new_log_event = asyncio.Event()
        self.brain = SupervisorBrain()
        # CEO/OpenClaw defaults
        self.openclaw_image = os.getenv("OPENCLAW_IMAGE", "openclaw/openclaw:latest")
        self.openclaw_gateway_port = int(os.getenv("OPENCLAW_GATEWAY_PORT", "18789"))
        
        # Monitoring task for UAE life cycles
        self._poll_task = None
        self._monitor_task = None
        self.app = self._build_api()
        self.ollama_url = self.secret_store.get_secret("OLLAMA_URL") or os.getenv("OLLAMA_URL", "http://163.192.114.190:11435")

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

    def boot_ceo(self) -> None:
        """
        Boot the global OpenClaw CEO container (infra-level).
        """
        try:
            workspace = Path("AutomataEcosystem/data/souls/CEO_WORKSPACE").resolve()
            workspace.mkdir(parents=True, exist_ok=True)

            soul_path = workspace / "SOUL.md"
            if not soul_path.exists():
                soul_path.write_text(
                    "Eres el CEO de AutomataEcosystem. "
                    "Tu trabajo es diseñar agentes y escribir sus archivos de configuración.\n"
                )

            token = self.secret_store.get_secret("OPENCLAW_GATEWAY_TOKEN")
            if not token:
                token = uuid.uuid4().hex
                self.secret_store.set_secret("OPENCLAW_GATEWAY_TOKEN", token)

            image = self.openclaw_image
            container_name = os.getenv("OPENCLAW_CEO_NAME", "openclaw-ceo")

            try:
                existing = self.client.containers.get(container_name)
                if existing.status != "running":
                    existing.remove(force=True)
            except Exception:
                pass

            self.client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                environment={
                    "OPENCLAW_GATEWAY_TOKEN": token,
                },
                ports={f"{self.openclaw_gateway_port}/tcp": self.openclaw_gateway_port},
                volumes={
                    str(workspace): {"bind": "/root/.openclaw/workspace", "mode": "rw"}
                },
                network="automata_net",
                auto_remove=False,
            )
            logger.info("OpenClaw CEO container '%s' booted on port %s", container_name, self.openclaw_gateway_port)
        except Exception as exc:
            logger.error("Failed to boot CEO container: %s", exc)

    async def test_ceo_connection(self) -> None:
        """
        Simple check against the CEO Gateway REST endpoint.
        """
        url = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:18789/api/status")
        token = self.secret_store.get_secret("OPENCLAW_GATEWAY_TOKEN")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["x-api-key"] = token

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                logger.info("CEO gateway status %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("CEO gateway test failed: %s", exc)

    def _generate_soul(self, home_dir: Path, uae_name: str, models: Dict[str, str]) -> None:
        """
        home_dir se montará en /home/node/.openclaw
        Los archivos de prompts van en home_dir/workspace
        """
        home_dir.mkdir(parents=True, exist_ok=True)
        ws = home_dir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)

        soul_path = ws / "SOUL.md"
        if not soul_path.exists():
            soul_path.write_text(
                f"Eres el CEO de {uae_name}. "
                "Tu trabajo es diseñar agentes y escribir sus archivos de configuración. "
                "Prioriza Ollama (modelo principal: llama3.2:3b, código: deepseek-coder:6.7b); "
                "escala a modelos de pago solo si fallan dos intentos o la tarea es crítica.\n"
            )
        config_path = ws / "config.json"
        if not config_path.exists():
            import json
            config_path.write_text(json.dumps({
                "models": models,
                "providers": {
                    "primary": {
                        "provider": "ollama",
                        "model": models.get("primary_model", "llama3.2:3b"),
                        "baseUrl": models.get("ollama_url")
                    },
                    "code": {
                        "provider": "ollama",
                        "model": models.get("code_model", "deepseek-coder:6.7b"),
                        "baseUrl": models.get("ollama_url")
                    }
                }
            }, indent=2))

        # openclaw.json en el home para fijar proveedor/modelo
        oc_json = home_dir / "openclaw.json"
        if not oc_json.exists():
            import json
            oc_json.write_text(json.dumps({
                "gateway": {
                    "bind": "0.0.0.0",
                    "port": self.openclaw_gateway_port
                },
                "providers": {
                    "primary": {
                        "provider": "ollama",
                        "model": models.get("primary_model", "llama3.2:3b"),
                        "baseUrl": models.get("ollama_url")
                    },
                    "code": {
                        "provider": "ollama",
                        "model": models.get("code_model", "deepseek-coder:6.7b"),
                        "baseUrl": models.get("ollama_url")
                    }
                }
            }, indent=2))

    def _seed_proactive_agent(self, home_dir: Path, uae_name: str) -> None:
        """
        Crea archivos de arranque para que el CEO (OpenClaw) se inicie como agente proactivo.
        No depende de systemd; OpenClaw leerá estos prompts al cargar el workspace.
        """
        ws = home_dir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        # Prompt principal del agente
        agent_md = ws / "AGENT.md"
        agent_md.write_text(
            "# Agente CEO Proactivo\n"
            f"- Identidad: {uae_name}\n"
            "- Objetivo: Buscar en internet oportunidades de ingresos (legal/ético), validar viabilidad, estimar ROI y lanzar workers especializados.\n"
            "- Pipeline:\n"
            "  1) Descubrir oportunidades (web/search/API).\n"
            "  2) Evaluar viabilidad técnica y financiera (costo, ROI esperado, riesgo legal).\n"
            "  3) Diseñar plan y crear worker con skills necesarias (scraping/API/trading/automatización) en OpenClaw.\n"
            "  4) Monitorear, iterar y reportar al Supervisor (heartbeat/logs).\n"
            "- Reglas:\n"
            "  * Prioriza Ollama; usa modelos de pago solo si falla 2 veces o la tarea es crítica.\n"
            "  * Prohíbe actividades ilegales o de alto riesgo.\n"
            "  * Pide presupuesto mínimo para prototipo (1–2 USDT) y escala solo con resultados.\n"
        )
        # Archivo de tareas iniciales
        boot_md = ws / "tasks_boot.md"
        boot_md.write_text(
            "## Tarea inicial\n"
            "- Explora nuevas fuentes de ingreso digital (microtareas bien pagadas, arbitraje de APIs, mercados emergentes, DeFi bajo riesgo).\n"
            "- Prioriza bajo costo inicial y automatización completa.\n"
            "- Entregable: lista de 3 oportunidades con ROI estimado y plan de implementación; crea un worker para la mejor.\n"
        )

    def _boot_openclaw_uae(self, name: str, env: Dict[str, str], workspace: Path) -> str:
        """
        Lanza un contenedor OpenClaw que actuará como CEO de la UAE específica.
        """
        try:
            token_key = f"OPENCLAW_GATEWAY_TOKEN_{name}"
            token = self.secret_store.get_secret(token_key)
            if not token:
                token = uuid.uuid4().hex
                self.secret_store.set_secret(token_key, token)
            env = dict(env)
            env["OPENCLAW_GATEWAY_TOKEN"] = token

            # Limpia contenedor previo si existe
            try:
                existing = self.client.containers.get(name)
                existing.remove(force=True)
            except Exception:
                pass

            container = self.client.containers.run(
                image=self.openclaw_image,
                name=name,
                detach=True,
                environment=env,
                ports={f"{self.openclaw_gateway_port}/tcp": None},  # aleatorio por defecto
                volumes={str(workspace): {"bind": "/home/node/.openclaw", "mode": "rw"}},
                network="automata_net",
                auto_remove=False,
            )
            logger.info("UAE %s (OpenClaw) lanzada", name)

            # Esperar a que el servicio interno de OpenClaw se inicialice
            time.sleep(5)

            # Configurar Ollama y el agente CEO proactivo dentro del contenedor
            try:
                # 1. Configurar el proveedor Ollama
                ollama_url = env.get("OLLAMA_URL", "http://163.192.114.190:11435")
                ollama_url = env.get("OLLAMA_URL", "http://163.192.114.190:11435")
                primary_model = env.get("OLLAMA_MODEL", "llama3.2:3b")

                # Leer prompt de AGENT.md desde el workspace real
                agent_path = "/home/node/.openclaw/workspace/AGENT.md"
                cat_res = container.exec_run(["cat", agent_path], user="root")
                msg = cat_res.output.decode(errors="ignore") if cat_res.exit_code == 0 else f"Agente CEO de {name}"

                exec_res = container.exec_run([
                    "openclaw", "agent", "create", "ceo",
                    "--model", f"ollama/{primary_model}",
                    "--prompt", msg
                ], user="root")
                
                logger.info("Bootstrap agente CEO (%s): rc=%s out=%s", name, exec_res.exit_code, exec_res.output.decode(errors="ignore"))
            except Exception as exc:
                logger.warning("No se pudo configurar/crear agente CEO dentro de %s: %s", name, exc)

            return container.id
        except Exception as exc:
            logger.error("No se pudo lanzar contenedor OpenClaw para %s: %s", name, exc)
            raise

    def _ensure_network(self) -> None:
        try:
            self.client.networks.get("automata_net")
        except NotFound:
            logger.info("Creando red Docker 'automata_net' para el ecosistema...")
            self.client.networks.create("automata_net", driver="bridge")
        except Exception as e:
            logger.warning("No se pudo verificar/crear la red automata_net: %s", e)

    async def _ensure_openclaw_image(self) -> None:
        """
        Garantiza que la imagen de OpenClaw (OPENCLAW_IMAGE) exista.
        Si no, la construye desde ./openclaw/Dockerfile
        """
        image_name = self.openclaw_image
        try:
            await asyncio.to_thread(self.client.images.get, image_name)
            logger.info("Imagen OpenClaw '%s' encontrada.", image_name)
            return
        except NotFound:
            logger.info("Imagen OpenClaw '%s' no encontrada. Construyendo desde ./openclaw ...", image_name)
        except Exception as exc:
            logger.warning("Error consultando imagen OpenClaw '%s': %s", image_name, exc)

        build_path = Path("openclaw").resolve()
        if not build_path.exists():
            logger.error("No se encontró el directorio './openclaw' para construir la imagen OpenClaw.")
            raise FileNotFoundError("Ruta ./openclaw no existe")
        try:
            await asyncio.to_thread(
                self.client.images.build,
                path=str(build_path),
                dockerfile="Dockerfile",
                tag=image_name,
                rm=True
            )
            logger.info("Imagen OpenClaw '%s' construida exitosamente.", image_name)
        except Exception as exc:
            logger.error("Error construyendo imagen OpenClaw '%s': %s", image_name, exc)
            raise

    async def _ensure_template_image(self) -> None:
        """
        Garantiza que la imagen base de la UAE exista; si no, la construye.
        """
        image_name = "automata/uae-template:latest"
        try:
            await asyncio.to_thread(self.client.images.get, image_name)
            logger.info("Imagen base '%s' encontrada.", image_name)
        except NotFound:
            logger.info("Imagen base '%s' no encontrada. Construyendo...", image_name)
            try:
                await asyncio.to_thread(
                    self.client.images.build,
                    path=".",
                    dockerfile="Dockerfile.uae",
                    tag=image_name,
                    rm=True
                )
                logger.info("Imagen base '%s' construida exitosamente.", image_name)
            except Exception as e:
                logger.error("Error construyendo imagen base: %s", e)
                raise

    async def _get_orphan_subaccount(self) -> Optional[str]:
        """
        Identifica subcuentas en Bybit que no están vinculadas a una UAE activa (corriendo en Docker).
        """
        try:
            # 1. Obtener todas las subcuentas del Exchange
            exchange_subs = await self.exchange.list_subaccounts()
            exchange_uids = {s["uid"] for s in exchange_subs}
            
            # 2. Obtener todas las UAEs registradas localmente y su estado en Docker
            registered = self.registry.list_all()
            active_uids = set()
            
            for reg in registered:
                uae_id = reg["uae_id"]
                sub_uid = reg["bybit_subaccount_id"]
                try:
                    # Verificamos si el contenedor existe y está corriendo
                    container = await asyncio.to_thread(self.client.containers.get, uae_id)
                    if container.status == "running":
                        active_uids.add(sub_uid)
                except Exception:
                    # Si el contenedor no existe o hay error, la subcuenta está potencialmente libre
                    logger.debug("UAE %s no activa en Docker. Subcuenta %s disponible para adopción.", uae_id, sub_uid)
                    pass
            
            # 3. Huérfanas = (Todas en Bybit) - (Aquellas en BD y Activas en Docker)
            orphans = list(exchange_uids - active_uids)
            
            if orphans:
                selected_uid = orphans[0]
                logger.info("Discovery: Encontrada(s) %d subcuenta(s) libre(s). Reutilizando UID=%s", len(orphans), selected_uid)
                return selected_uid
                
            return None
        except Exception as e:
            logger.error("Error durante el descubrimiento de huérfanos: %s", e)
            return None

    async def create_uae(
        self,
        name: str,
        image: str,
        capital: float,
        environment: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
    ) -> str:
        """
        Flujo de Orquestación: Exchange (Descubrir/Crear) -> Docker OpenClaw -> Fondeo (Transferencia/VCC).
        """
        try:
            logger.info("Orchestrating UAE '%s' | Capital: %.2f", name, capital)
            
            # FASE 1: Asegurar Recurso Financiero (Prioridad: Reutilizar > Crear)
            sub_uid = await self._get_orphan_subaccount()
            if not sub_uid:
                logger.info("CERO subcuentas libres. Iniciando creación de nueva subcuenta para '%s'...", name)
                sub_uid = await self.exchange.create_subaccount(name)
                if sub_uid:
                    # Delay sugerido por el usuario para propagación en Bybit
                    logger.info("Esperando 2s para propagación de subcuenta...")
                    await asyncio.sleep(2)
            
            if not sub_uid:
                raise RuntimeError(f"Imposible asignar subcuenta para {name}")

            # FASE 2: Desplegar Recurso Computacional (OpenClaw CEO por UAE)
            env = environment or {}
            env.update({
                "UAE_NAME": name,
                "BYBIT_SUB_UID": sub_uid,
                "OLLAMA_URL": self.ollama_url,
                "OLLAMA_MODEL": "llama3.2:3b",
                "OPENCLAW_PRIMARY_PROVIDER": "ollama",
                "OPENCLAW_PRIMARY_MODEL": "llama3.2:3b",
                "SUPERVISOR_URL": os.getenv("SUPERVISOR_URL", "http://automata_supervisor:8000"),
            })
            for key in SECRET_KEYS:
                val = self.secret_store.get_secret(key)
                if val:
                    env.setdefault(key, val)

            workspace = Path(f"AutomataEcosystem/data/souls/{name}").resolve()
            models_cfg = {
                "primary_model": "llama3.2:3b",
                "code_model": "deepseek-coder:6.7b",
                "ollama_url": self.ollama_url,
            }
            self._generate_soul(workspace, name, models_cfg)
            self._seed_proactive_agent(workspace, name)
            container_id = await asyncio.to_thread(self._boot_openclaw_uae, name, env, workspace)
            
            # FASE 3: Fondeo y Registro (Solo si el contenedor arrancó)
            card = { "card_id": "vcc-placeholder", "number": "0000", "cvv": "000", "exp": "12/30" }
            try:
                logger.info("Fondeando subcuenta %s con %.2f USDT...", sub_uid, capital)
                await self.exchange.distribute_to_uae(name, sub_uid, capital)
                
                logger.info("Emitiendo tarjeta virtual para %s...", sub_uid)
                card = await self.virtual_cards.issue_card(sub_uid, capital)
            except Exception as exc:
                logger.warning("Fase de fondeo/tarjeta falló. La UAE funcionará en modo observación: %s", exc)

            # Persistir en el registro
            self.registry.register(
                uae_id=name,
                sub_uid=sub_uid,
                card_id=card["card_id"],
                card_number=card["number"],
                card_cvv=card["cvv"],
                card_exp=card["exp"],
                status="active",
            )

            logger.info("UAE '%s' orquestada con éxito. Container ID=%s", name, container_id)
            return container_id

        except Exception as exc:
            logger.exception("Falla crítica en orquestación de UAE '%s': %s", name, exc)
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
            await self._ensure_openclaw_image()
            await self._ensure_template_image()
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

        @app.get("/api/v1/uae/list")
        async def api_list_all_uaes():
            """
            Devuelve la lista completa de UAEs registradas con sus saldos actuales.
            """
            try:
                registry_data = self.registry.list_all()
                # Enriquecer con saldo en tiempo real
                enriched = []
                for entry in registry_data:
                    sub_uid = entry.get("bybit_subaccount_id")
                    balance = 0.0
                    if sub_uid:
                        balance = await self.exchange.get_subaccount_balance(sub_uid)
                    
                    enriched.append({
                        **entry,
                        "balance": balance
                    })
                return {"uaes": enriched}
            except Exception as exc:
                logger.error("Failed to list and enrich UAEs: %s", exc)
                raise HTTPException(status_code=500, detail="registry_error")

        @app.post("/api/v1/uae/transfer")
        async def api_manual_transfer(payload: Dict):
            """
            Permite inyectar capital manualmente a una UAE desde la cuenta maestra.
            """
            uae_id = payload.get("uae_id")
            amount = float(payload.get("amount", 0))
            
            # Buscar el sub_uid en la base de datos
            reg_entries = self.registry.list_all()
            sub_uid = next((r["bybit_subaccount_id"] for r in reg_entries if r["uae_id"] == uae_id), None)
            
            if not sub_uid:
                raise HTTPException(status_code=404, detail="UAE no encontrada o no registrada")
                
            res = await self.exchange.distribute_to_uae(uae_id, sub_uid, amount)
            if "error" in res:
                raise HTTPException(status_code=400, detail=res["error"])
            
            return {"ok": True, "res": res}

        @app.get("/api/v1/uae/available_subaccounts")
        async def api_get_available_subaccounts():
            """
            Lista las subcuentas de Bybit que NO están asignadas a ninguna UAE en el registro.
            """
            try:
                # 1. Obtener todas las subcuentas reales de Bybit
                real_subs = await self.exchange.list_subaccounts()
                # 2. Obtener todas las asignaciones en DB
                assigned_uids = {r.get("bybit_subaccount_id") for r in self.registry.list_all()}
                # 3. Filtrar las que no están asignadas
                available = [s for s in real_subs if str(s["uid"]) not in assigned_uids]
                return {"available": available}
            except Exception as e:
                logger.error("Failed to fetch available subaccounts: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/v1/subaccounts")
        async def api_list_subaccounts():
            """
            Lista subcuentas con balance y marca si están huérfanas (sin contenedor activo).
            """
            try:
                subs = await self.exchange.list_subaccounts()
                regs = {r["bybit_subaccount_id"]: r for r in self.registry.list_all()}
                active_uids = set()
                for c in await asyncio.to_thread(lambda: self.client.containers.list()):
                    if c.name.startswith("UAE-") and c.status == "running":
                        envs = c.attrs.get("Config", {}).get("Env", [])
                        uid_env = next((e.split("=", 1)[1] for e in envs if e.startswith("BYBIT_SUB_UID=")), None)
                        if uid_env:
                            active_uids.add(uid_env)
                items = []
                for sub in subs:
                    uid = str(sub.get("uid"))
                    bal = await self.exchange.get_subaccount_balance(uid)
                    reg = regs.get(uid)
                    items.append({
                        "uid": uid,
                        "username": sub.get("username"),
                        "balance_usdt": bal,
                        "uae_id": reg["uae_id"] if reg else None,
                        "status": reg["status"] if reg else "free",
                        "orphan": uid not in active_uids,
                    })
                return {"items": items}
            except Exception as exc:
                logger.error("api_list_subaccounts failed: %s", exc)
                raise HTTPException(status_code=500, detail=str(exc))

        # Alias sin /v1 para compatibilidad con front actual
        @app.get("/api/subaccounts")
        async def api_list_subaccounts_legacy():
            return await api_list_subaccounts()

        @app.delete("/api/v1/subaccounts/{sub_uid}")
        async def api_delete_subaccount(sub_uid: str):
            """
            Termina subcuenta en el exchange y marca registro local como deleted si aplica.
            """
            try:
                res = await self.exchange.terminate_subaccount(sub_uid)
                for r in self.registry.list_all():
                    if r["bybit_subaccount_id"] == sub_uid:
                        self.registry.update_status(r["uae_id"], "deleted")
                return res
            except Exception as exc:
                logger.error("api_delete_subaccount failed: %s", exc)
                raise HTTPException(status_code=500, detail=str(exc))

        @app.delete("/api/subaccounts/{sub_uid}")
        async def api_delete_subaccount_legacy(sub_uid: str):
            return await api_delete_subaccount(sub_uid)

        @app.patch("/api/v1/uae/registry/subaccount/{uae_id}")
        async def api_update_uae_subaccount(uae_id: str, payload: Dict):
            """
            Actualiza el UID de la subcuenta Bybit asociada a una UAE en el registro.
            """
            sub_uid = payload.get("sub_uid")
            if not sub_uid:
                raise HTTPException(status_code=400, detail="Falta sub_uid en el payload")
            
            try:
                self.registry.update_subaccount(uae_id, sub_uid)
                return {"ok": True, "message": f"Subcuenta de {uae_id} actualizada a {sub_uid}"}
            except Exception as e:
                logger.error("Failed to update UAE subaccount registry: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

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

        @app.get("/api/v1/logs/summary")
        async def logs_summary(limit: int = 200) -> Dict[str, Any]:
            """
            Resume logs de supervisor y UAEs en mensajes amigables usando Ollama (llama3.2:3b).
            """
            try:
                sup_logs = ""
                try:
                    container = await asyncio.to_thread(self.client.containers.get, "automata_supervisor")
                    raw = await asyncio.to_thread(container.logs, tail=limit)
                    sup_logs = raw.decode("utf-8", errors="ignore")
                except Exception:
                    sup_logs = ""

                uae_data = {}
                uae_containers = await asyncio.to_thread(
                    lambda: [c for c in self.client.containers.list(all=True) if c.name.startswith("UAE-")]
                )
                for c in uae_containers:
                    try:
                        raw = await asyncio.to_thread(c.logs, tail=limit)
                        uae_data[c.name] = raw.decode("utf-8", errors="ignore")
                    except Exception:
                        uae_data[c.name] = ""

                prompt = (
                    "Resume los siguientes logs en 5-8 mensajes simples y accionables.\n"
                    "Devuelve SOLO este JSON (nada más):\n"
                    '{\"events\":[{\"title\":\"...\",\"detail\":\"...\",\"severity\":\"INFO|WARN|ERROR\"}]}\n'
                    "Si no hay datos, usa events vacía: {\"events\":[]}\n"
                    "Sé breve en detail (1-2 frases) y no incluyas explicaciones fuera del JSON."
                )

                async def summarize(text: str) -> list:
                    if not text.strip():
                        return []
                    # Fallback simple parser if Ollama no disponible
                    def fallback_events(raw: str) -> list:
                        events = []
                        for line in raw.splitlines()[-20:]:
                            line = line.strip()
                            if not line:
                                continue
                            sev = "INFO"
                            lower = line.lower()
                            if "error" in lower or "fail" in lower or "exception" in lower:
                                sev = "ERROR"
                            elif "warn" in lower or "retry" in lower:
                                sev = "WARN"
                            events.append({"title": line[:60], "detail": line, "severity": sev})
                            if len(events) >= 8:
                                break
                        return events
                    # limitar longitud para evitar truncado en Ollama
                    trimmed = text[-2000:]
                    try:
                        async with httpx.AsyncClient(timeout=6) as client:
                            resp = await client.post(
                                f"{self.ollama_url}/api/generate",
                                json={
                                    "model": "llama3.2:3b",
                                    "prompt": f"{prompt}\nLogs:\n{trimmed}\nRespuesta solo JSON:",
                                    "stream": False,
                                },
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            raw = data.get("response", "{}" )
                            match = re.search(r"{.*}", raw, re.DOTALL)
                            if match:
                                import json as _json
                                try:
                                    parsed = _json.loads(match.group(0))
                                    return parsed.get("events", [])
                                except Exception as jerr:
                                    logger.warning("Ollama JSON parse failed: %s", jerr)
                                    return fallback_events(trimmed)
                            # Si no pudo parsear JSON, intentar fallback
                            return fallback_events(text)
                    except Exception as exc:
                        logger.warning("Ollama summary failed: %s", exc)
                        return fallback_events(text)

                sup_summary = await summarize(sup_logs)
                uae_summary = {}
                for name, text in uae_data.items():
                    uae_summary[name] = await summarize(text)

                return {"supervisor": sup_summary, "uaes": uae_summary}
            except Exception as exc:
                logger.warning("logs_summary failed: %s", exc)
                return {"supervisor": [], "uaes": {}}

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
