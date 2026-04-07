"""
UAE CEO process (Bybit).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict

import httpx
from pybit.unified_trading import HTTP
from rich.console import Console
from rich.theme import Theme

from AutomataEcosystem.core.database import DiscoveredSectors, EncryptedSecretStore
from AutomataEcosystem.uae.brain import BrainAgent
from AutomataEcosystem.uae.research_tool import ResearchTool
from AutomataEcosystem.uae.openclaw_manager import OpenClawManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("uae.main_agent")

SUPERVISOR_URL = os.getenv("SUPERVISOR_URL", "http://supervisor:8000")
UAE_ID = os.getenv("UAE_NAME", os.getenv("HOSTNAME", "unknown-uae"))
POLL_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
SUB_UID = os.getenv("BYBIT_SUB_UID")

uae_log_buffer = []  # Buffer temporal de logs para enviar al supervisor
console = Console(theme=Theme({"good": "green", "bad": "red", "info": "cyan"}))


def build_bybit_client(store: EncryptedSecretStore) -> HTTP:
    api_key = store.get_secret("BYBIT_API_KEY") or os.getenv("BYBIT_API_KEY", "")
    api_secret = store.get_secret("BYBIT_API_SECRET") or os.getenv("BYBIT_API_SECRET", "")
    testnet = not (api_key and api_secret)
    return HTTP(testnet=testnet, api_key=api_key, api_secret=api_secret)


async def fetch_balances(client: HTTP) -> Dict[str, float]:
    try:
        kwargs = {"accountType": "UNIFIED", "coin": "USDT,USDC"}
        if SUB_UID:
            kwargs["memberId"] = SUB_UID
        res = await asyncio.to_thread(client.get_wallet_balance, **kwargs)
        coin_list = res.get("result", {}).get("list", [])
        balances = {"USDT": 0.0, "USDC": 0.0}
        if coin_list:
            for coin in coin_list[0].get("coin", []):
                name = coin.get("coin")
                if name in balances:
                    balances[name] = float(coin.get("walletBalance", 0))
        return balances
    except Exception as exc:
        logger.warning("Bybit balance fetch failed: %s", exc)
        return {"USDT": 0.0, "USDC": 0.0}


async def post_heartbeat(payload: Dict) -> None:
    url = f"{SUPERVISOR_URL}/api/v1/heartbeat"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("Heartbeat sent: %s", resp.text)
    except Exception as exc:
        logger.warning("Failed to send heartbeat: %s", exc)


async def main_loop() -> None:
    store = EncryptedSecretStore()
    client = build_bybit_client(store)
    brain = BrainAgent(SUPERVISOR_URL)
    research = ResearchTool()
    claw = OpenClawManager()
    sectors_db = DiscoveredSectors(store)
    prototype_tracker = None

    while True:
        # a) Buscar oportunidad
        opp = research.find_opportunity()
        task_prompt = f"Sector: {opp.get('sector')} | Query: {opp.get('query')} | Lead: {opp.get('lead')}"
        msg = f"[BUSCANDO] {task_prompt}"
        console.log(f"[cyan]{msg}[/cyan]")
        uae_log_buffer.append(msg)

        # Filtro de seguridad LLM
        safe = await brain.check_safety(opp)
        if not safe:
            msg = f"SEGURIDAD: ❌ {task_prompt}"
            console.log(f"[bad]{msg}[/bad]")
            uae_log_buffer.append(msg)
            await asyncio.sleep(POLL_INTERVAL)
            continue
        
        msg = f"SEGURIDAD: ✅ {task_prompt}"
        console.log(f"[good]{msg}[/good]")
        uae_log_buffer.append(msg)

        # Análisis de factibilidad
        feasibility = await brain.feasibility_analysis(opp)
        feasible = all(feasibility.values())
        if not feasible:
            console.log(f"[bad][FACTIBILIDAD: ❌][/bad] {feasibility}")
            await asyncio.sleep(POLL_INTERVAL)
            continue
        console.log(f"[good][FACTIBILIDAD: ✅][/good] {feasibility}")

        # b) Intentar programar solución local
        success, code = await brain.solve_task(task_prompt, critical=opp.get("sector") == "DeFi")

        # c) Enviar a OpenClaw si exitoso
        if success:
            try:
                # Registrar descubrimiento y pedir presupuesto al supervisor
                sectors_db.upsert(sector_name=opp.get("query", "Unknown"), uae_id=UAE_ID, status="prototyping")
                budget_amount = 1.0 if opp.get("sector") == "Unknown" else 0.0
                approved = False
                if budget_amount > 0:
                    try:
                        async with httpx.AsyncClient(timeout=10) as client_http:
                            resp = await client_http.post(
                                f"{SUPERVISOR_URL}/api/v1/request_spending",
                                json={"uae_id": UAE_ID, "amount": budget_amount, "reason": task_prompt},
                            )
                            resp.raise_for_status()
                            console.log(f"[good][PRESUPUESTO APROBADO][/good] {resp.text}")
                            approved = True
                    except Exception as exc:
                        console.log(f"[bad]Presupuesto rechazado/err: {exc}[/bad]")
                        approved = False
                else:
                    approved = True

                if not approved:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                worker_env = {"TASK_PROMPT": task_prompt, "UAE_ID": UAE_ID}
                if opp.get("sector") == "Unknown":
                    worker_env["BUDGET_USDT"] = str(budget_amount)
                worker_id = claw.spawn_worker(
                    name=f"worker-{UAE_ID}",
                    image="automata/uae-template:latest",
                    environment=worker_env,
                )
                console.log(f"[good][WORKER LANZADO][/good] {worker_id}")
                if opp.get("sector") == "Unknown":
                    balances_now = await fetch_balances(client)
                    prototype_tracker = {
                        "worker_id": worker_id,
                        "start_bal": balances_now.get("USDT", 0),
                        "cycles": 3,
                        "sector_key": opp.get("query", "Unknown"),
                    }
            except Exception as exc:
                console.log(f"[bad]No se pudo lanzar worker: {exc}[/bad]")
        else:
            console.log("[bad]No se pudo resolver localmente; código incompleto[/bad]")

        # Heartbeat con balances y logs
        balances = await fetch_balances(client)
        payload = {
            "uae_id": UAE_ID, 
            "status": "alive", 
            "balances": balances,
            "logs": list(uae_log_buffer)
        }
        console.log(f"[info]Heartbeat {UAE_ID} | logs: {len(uae_log_buffer)}[/info]")
        await post_heartbeat(payload)
        uae_log_buffer.clear() # Limpiar buffer tras envío exitoso

        # Monitoreo de prototipo
        if prototype_tracker:
            prototype_tracker["cycles"] -= 1
            bal = balances.get("USDT", 0)
            if bal > prototype_tracker["start_bal"]:
                sectors_db.upsert(prototype_tracker["sector_key"], UAE_ID, "profitable")
                console.log(f"[good]Nuevo sector rentable: {prototype_tracker['sector_key']}[/good]")
                prototype_tracker = None
            elif prototype_tracker["cycles"] <= 0:
                sectors_db.upsert(prototype_tracker["sector_key"], UAE_ID, "failed")
                try:
                    claw.kill_worker(prototype_tracker["worker_id"])
                except Exception:
                    pass
                console.log(f"[bad]Prototipo fallido: {prototype_tracker['sector_key']}[/bad]")
                prototype_tracker = None

        await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
