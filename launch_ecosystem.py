"""
Main entrypoint to launch Supervisor and trigger UAE-Alpha.
"""

from __future__ import annotations

import asyncio
from rich.console import Console
import uvicorn

from AutomataEcosystem.core.database import (
    EncryptedSecretStore,
    UaeRegistry,
    ModelAuditLog,
    DiscoveredSectors,
)
from AutomataEcosystem.core.supervisor import Supervisor

console = Console()


def init_db():
    store = EncryptedSecretStore()
    UaeRegistry(store)
    ModelAuditLog(store)
    DiscoveredSectors(store)
    console.log("[green]Base de datos inicializada[/green]")
    return store


async def start_supervisor(store: EncryptedSecretStore):
    supervisor = Supervisor(genesis_wallet_id="GENESIS_WALLET", secret_store=store)
    config = uvicorn.Config(supervisor.app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    console.log("[cyan]Supervisor escuchando en 0.0.0.0:8000[/cyan]")
    await server.serve()


async def main():
    store = init_db()
    await start_supervisor(store)


if __name__ == "__main__":
    asyncio.run(main())
