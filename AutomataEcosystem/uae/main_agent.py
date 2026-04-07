"""
UAE CEO process (Autonomous).
Uses localized UaeFinanceManager for subaccount operations via CCXT proxy.
"""

from __future__ import annotations

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, List

import httpx
from rich.console import Console
from rich.theme import Theme

from AutomataEcosystem.core.database import DiscoveredSectors, EncryptedSecretStore
from AutomataEcosystem.uae.brain import BrainAgent
from AutomataEcosystem.uae.research_tool import ResearchTool
from AutomataEcosystem.uae.openclaw_manager import OpenClawManager
from AutomataEcosystem.uae.finance_manager import UaeFinanceManager, UaeVirtualCardManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("uae.main_agent")

SUPERVISOR_URL = os.getenv("SUPERVISOR_URL", "http://supervisor:8000")
UAE_ID = os.getenv("UAE_NAME", os.getenv("HOSTNAME", "unknown-uae"))
POLL_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
SUB_UID = os.getenv("BYBIT_SUB_UID")

uae_log_buffer: List[str] = []
console = Console(theme=Theme({"good": "green", "bad": "red", "info": "cyan"}))


class LocalMemory:
    """
    Saves UAE's individual experience to a local JSON file.
    """
    def __init__(self, filename: str = "memory.json"):
        self.filename = filename
        self.data: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    return json.load(f)
                except:
                    return []
        return []

    def add_entry(self, entry: Dict):
        entry["timestamp"] = datetime.now().isoformat()
        self.data.append(entry)
        with open(self.filename, "w") as f:
            json.dump(self.data[-100:], f, indent=2)  # Keep last 100 entries

    def get_context(self) -> str:
        return "\n".join([f"- {d.get('msg')}" for d in self.data[-10:]])


class UaeAgent:
    def __init__(self, store: EncryptedSecretStore) -> None:
        self.store = store
        self.exchange = UaeFinanceManager()
        self.vcc = UaeVirtualCardManager(self.exchange)
        self.brain = BrainAgent(supervisor_url=SUPERVISOR_URL)
        self.research = ResearchTool()
        self.claw = OpenClawManager()
        self.sectors_db = DiscoveredSectors(store)
        self.memory = LocalMemory()
        logger.info("UAE Agent initialized: %s | UID: %s", UAE_ID, SUB_UID)

    async def bootstrap(self) -> bool:
        """
        Initial handshake with supervisor.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{SUPERVISOR_URL}/api/v1/uae/config/{UAE_ID}")
                resp.raise_for_status()
                self.config = resp.json()
                
                # Update sub-components with fetched config
                self.exchange.set_config(self.config)
                self.brain.set_config(self.config)
                
                logger.info("Bootstrap successful for %s. Sub-UID: %s", UAE_ID, self.config.get("sub_uid"))
                return True
        except Exception as e:
            logger.error("Bootstrap failed: %s", e)
            return False

    async def get_balances(self) -> Dict[str, float]:
        """
        Fetch balance from specialized localized finance manager.
        """
        return await self.exchange.get_balance()

    async def run(self) -> None:
        console.log(f"[info]Iniciando UAE Agent Autónomo: {UAE_ID}[/info]")
        
        # a) Bootstrap initial config
        if not await self.bootstrap():
            console.log("[bad]Error crítico: No se pudo obtener la configuración del Supervisor.[/bad]")
            return

        # Start heartbeat loop in background
        asyncio.create_task(self._heartbeat_loop())
        
        while True:
            try:
                # b) Consultar Inteligencia Colectiva (Estrategias previas)
                existing_strats = []
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(f"{SUPERVISOR_URL}/api/v1/strategies?limit=5")
                        if resp.ok:
                            existing_strats = resp.json()
                except:
                    pass

                # c) Buscar oportunidad propia o evaluar compartidas
                opp = self.research.find_opportunity()
                
                memory_context = self.memory.get_context()
                
                task_prompt = (
                    f"Memoria Local:\n{memory_context}\n\n"
                    f"Estrategias Exitosas Compartidas:\n{json.dumps(existing_strats, indent=2)}\n\n"
                    f"Nueva Oportunidad Detectada en sector {opp.get('sector')}: {opp.get('query')}.\n"
                    f"Detalle: {opp.get('lead')}.\n"
                    "Instrucción: Evalúa si es mejor replicar una estrategia exitosa o ejecutar la nueva oportunidad."
                )
                msg = f"[BUSCANDO] {opp.get('query')}"
                console.log(f"[cyan]{msg}[/cyan]")
                uae_log_buffer.append(msg)

                # Filtro de seguridad LLM
                safe = await self.brain.check_safety(opp)
                if not safe:
                    msg = f"SEGURIDAD: ❌ {opp.get('query')}"
                    console.log(f"[bad]{msg}[/bad]")
                    uae_log_buffer.append(msg)
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                
                msg = f"SEGURIDAD: ✅ {opp.get('query')}"
                uae_log_buffer.append(msg)

                # Análisis de factibilidad
                feasibility = await self.brain.feasibility_analysis(opp)
                feasible = all(feasibility.values())
                if not feasible:
                    msg = f"FACTIBILIDAD: ❌ {opp.get('query')}"
                    console.log(f"[bad]{msg}[/bad]")
                    uae_log_buffer.append(msg)
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                
                msg = f"FACTIBILIDAD: ✅ {opp.get('query')}"
                uae_log_buffer.append(msg)

                # b) Intentar programar solución local
                success, code = await self.brain.solve_task(task_prompt, critical=opp.get("sector") == "DeFi")

                # c) Ejecutar si exitoso
                if success:
                    msg = f"[EJECUTANDO] Solución para {opp.get('query')}"
                    console.log(f"[info]{msg}[/info]")
                    uae_log_buffer.append(msg)
                    
                    # Registrar en base de datos local
                    self.sectors_db.upsert(sector_name=opp.get("query", "Unknown"), uae_id=UAE_ID, status="prototyping")
                    
                    # Ejecutar en OpenClaw
                    result = await self.claw.execute(code)
                    
                    # d) Procesar resultado (ej: recolectar ganancias)
                    profit = result.get("profit", 0)
                    if profit > 0:
                        msg = f"[GANANCIA] Sector {opp.get('query')}: ${profit}"
                        console.log(f"[good]{msg}[/good]")
                        uae_log_buffer.append(msg)
                        self.memory.add_entry({"msg": msg, "profit": profit})
                        
                        # Reportar estrategia exitosa a la Inteligencia Colectiva
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                f"{SUPERVISOR_URL}/api/v1/strategies/report",
                                json={
                                    "uae_id": UAE_ID,
                                    "sector": opp.get("query"),
                                    "idea": task_prompt,
                                    "code": code,
                                    "status": "PROFITABLE",
                                    "profit": profit
                                }
                            )
                        self.sectors_db.upsert(sector_name=opp.get("query", "Unknown"), uae_id=UAE_ID, status="profitable")
                    else:
                        self.memory.add_entry({"msg": f"Fallo en {opp.get('query')}", "profit": 0})
                        self.sectors_db.upsert(sector_name=opp.get("query", "Unknown"), uae_id=UAE_ID, status="failed")

            except Exception as exc:
                logger.error("Error in UAE agent loop: %s", exc)
                uae_log_buffer.append(f"[ERROR] LOOP: {exc}")
            
            await asyncio.sleep(POLL_INTERVAL)

    async def _heartbeat_loop(self) -> None:
        """
        Periodically sends status, balances and logs to the supervisor.
        """
        while True:
            try:
                balances = await self.get_balances()
                
                # Consumir logs del buffer
                global uae_log_buffer
                logs_to_send = list(uae_log_buffer)
                uae_log_buffer = []  
                
                payload = {
                    "uae_id": UAE_ID,
                    "status": "active",
                    "balances": balances,
                    "logs": logs_to_send,
                }
                
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"{SUPERVISOR_URL}/api/v1/uae/heartbeat", json=payload)
                    
            except Exception as exc:
                logger.warning("Heartbeat failed: %s", exc)
                
            await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    store = EncryptedSecretStore()
    agent = UaeAgent(store)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("UAE Agent stopped by user")

if __name__ == "__main__":
    main()
