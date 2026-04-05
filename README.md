# AutomataEcosystem

Ecosistema de Agentes Económicos Autónomos (UAEs) con cerebro híbrido (Ollama remoto + Claude de respaldo), orquestado por un Supervisor en FastAPI y aislado en contenedores Docker.

## Arquitectura Actual
- **Supervisor (FastAPI)**: escucha en `:8000`, crea/termina UAEs, aplica impuestos, rebalancea liquidez Bybit, expone endpoints:
  - `POST /api/v1/heartbeat` – reportes de UAEs
  - `POST /api/v1/request_spending` – recarga VCC para prototipos
  - Background tasks: `monitor_ecosystem` (ignición automática, apoptosis, mitosis), `funding_poll`.
- **UAEs**: contenedores basados en `automata/uae-template:latest`.
  - `uae/main_agent.py`: busca oportunidades (DuckDuckGo), pasa filtro de seguridad LLM (Ollama), analiza factibilidad, genera código (Ollama→Claude solo si falla), lanza workers vía OpenClaw, pide presupuesto y marca sectores como profitable/failed.
  - `uae/brain.py`: escalado de razonamiento, validación de código, auditoría de llamadas a Claude.
- **Finanzas (Bybit)**: `core/finance_manager.py` usa pybit V5 para crear subcuentas, transferir fondos (universal o interna), rebalancear FUND/UNIFIED, auditar transferencias. VCC manager esqueleto con top-up.
- **Base de datos segura** (SQLite + Fernet): secretos y tablas `uae_registry`, `discovered_sectors`, `model_audit`, `transfer_audit`.
- **Launch script**: `launch_ecosystem.py` inicia DB, arranca Supervisor y deja que `monitor_ecosystem` lance UAEs automáticamente (cero teclado).

## Requisitos
- Docker y daemon activos (DooD: se monta `/var/run/docker.sock` en UAEs).
- Python 3.11+
- Credenciales Bybit (maestra) ya cargadas vía `scripts/setup_secrets.py`.
- Imagen base construida: `docker build -t automata/uae-template:latest .`

## Variables clave
- `BYBIT_API_KEY`, `BYBIT_API_SECRET`, `BYBIT_MASTER_UID` (en la bóveda).
- `OLLAMA_URL` (inyectado por Supervisor): `http://100.122.166.17:11435`
- `SUPERVISOR_URL` (UAEs): `http://supervisor:8000`

## Cómo arrancar
```bash
python launch_ecosystem.py
# el Supervisor arranca en 0.0.0.0:8000 y monitor_ecosystem lanzará UAE-Alpha si no hay UAEs
```

## Flujo autónomo
1) `monitor_ecosystem` lanza UAE-Alpha con 2 USDT si no hay UAEs.
2) UAE busca oportunidades → seguridad LLM → factibilidad → genera código → lanza worker prototipo (budget 1 USDT si sector desconocido).
3) Heartbeat + balances se envían al Supervisor; request_spending recarga VCC.
4) Si balance de subcuenta sube → sector `profitable` → mitosis (clon). Si baja/falla → apoptosis.

## Directorios clave
- `AutomataEcosystem/core/` – supervisor, finanzas, DB segura.
- `AutomataEcosystem/uae/` – brain, main_agent, research_tool, openclaw_manager.
- `scripts/setup_secrets.py` – carga credenciales cifradas.
- `Dockerfile` / `Dockerfile.uae` – imágenes host y UAEs.

## Notas de operación
- Supervisor usa la arquitectura nativa del host (sin `platform` fijo).
- Para limpiar un contenedor atascado: `docker rm -f UAE-Alpha`.
- Logs en vivo: `docker logs -f <nombre_contenedor>`.

## Roadmap inmediato
- Integrar API real de VCC en `VirtualCardManager`.
- Endpoint de aprobación explícita para Claude en el Supervisor.
- Métricas y salud vía FastAPI (Prometheus/healthcheck).
