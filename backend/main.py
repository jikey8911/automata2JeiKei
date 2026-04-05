import os
import asyncio
import json
from datetime import datetime
from typing import Set, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from utils.auth import create_access_token, verify_password, get_current_user, Token

from adaptadores.postgres_adapter import PostgresAdapter
from adaptadores.duckduckgo_adapter import DuckDuckGoAdapter
from adaptadores.ollama_adapter import OllamaAdapter
from adaptadores.appium_adapter import AppiumAdapter
from adaptadores.binance_adapter import BinanceAdapter
from adaptadores.dolarapp_adapter import DolarAppAdapter
from dominio.agente import AgenteAutonomo
from rutas_avanzadas import router as router_avanzado
from rutas_configuracion import router as router_configuracion
from rutas_billeteras import router as router_billeteras

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://automata:automata_secure_password@db:5432/automata_ai")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

# Inicializar adaptadores
repositorio = PostgresAdapter(DATABASE_URL)
buscador = DuckDuckGoAdapter()
generador_lenguaje = OllamaAdapter(OLLAMA_BASE_URL)

# Crear adaptadores adicionales
automatizador = AppiumAdapter()
servicio_financiero = BinanceAdapter()
respaldo_financiero = DolarAppAdapter(repositorio)

# Crear agente
agente = AgenteAutonomo(
    repositorio=repositorio,
    buscador=buscador,
    generador_lenguaje=generador_lenguaje,
    automatizador=automatizador,
    servicio_financiero=servicio_financiero,
    respaldo_financiero=respaldo_financiero
)

# Crear aplicación FastAPI
app = FastAPI(
    title="AutomataAI - Agente Autónomo de Generación de Ingresos",
    description="Sistema de IA autónomo que genera ingresos 24/7",
    version="1.0.0"
)

# CORS
origins = [
    "http://163.192.114.190:3000",
    "http://localhost:3000",
    "http://automata_frontend:3000",
    "http://frontend:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(router_avanzado)
app.include_router(router_configuracion)
app.include_router(router_billeteras)

# Gestión de WebSockets conectados
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error enviando mensaje: {e}")


manager = ConnectionManager()

# Modelos Pydantic
class EstadoAgente(BaseModel):
    estado_actual: str
    ingresos_totales: float
    modelos_activos: int
    modelos_exitosos: int
    modelos_fallidos: int
    tasa_exito: float
    ciclos_completados: int


class ControlAgente(BaseModel):
    accion: str  # "iniciar", "pausar", "reanudar"


# Rutas de Autenticación
@app.post("/api/auth/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint para iniciar sesión y obtener token JWT"""
    user = await repositorio.obtener_usuario(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me")
async def read_users_me(current_user: Any = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    user = await repositorio.obtener_usuario(current_user.username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # No devolver el hash de la contraseña
    user_info = dict(user)
    user_info.pop("password_hash")
    return user_info


# Rutas HTTP
@app.get("/api/health")
async def health_check():
    """Verificar salud del servidor"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "agente_estado": agente.estado_actual.value
    }


@app.get("/api/status")
async def obtener_status(current_user: Any = Depends(get_current_user)):
    """Obtener estado actual del agente y KPIs"""
    try:
        estado_bd = await repositorio.obtener_estado_agente()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "estado_actual": agente.estado_actual.value,
            "ingresos_totales": agente.ingresos_totales,
            "modelos_activos": len([m for m in agente.modelos_activos if m.estado == "activo"]),
            "modelos_exitosos": len([m for m in agente.modelos_activos if m.estado == "exitoso"]),
            "modelos_fallidos": len([m for m in agente.modelos_activos if m.estado == "fallido"]),
            "ciclos_completados": agente.ciclos_completados,
            "base_datos": estado_bd
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/modelos")
async def obtener_modelos(estado: str = None, current_user: Any = Depends(get_current_user)):
    """Obtener lista de modelos de ingresos"""
    try:
        modelos = await repositorio.obtener_todos_modelos(estado=estado)
        
        return {
            "total": len(modelos),
            "modelos": [
                {
                    "id": str(m.id),
                    "estrategia_nombre": m.estrategia_nombre,
                    "estado": m.estado,
                    "ingresos_generados": m.ingresos_generados,
                    "fecha_creacion": m.fecha_creacion.isoformat(),
                    "descripcion": m.descripcion
                }
                for m in modelos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/control")
async def controlar_agente(control: ControlAgente, current_user: Any = Depends(get_current_user)):
    """Controlar el agente (iniciar, pausar, reanudar)"""
    try:
        if control.accion == "iniciar":
            # Iniciar ciclo del agente en background
            asyncio.create_task(agente.ejecutar_ciclo())
            return {"mensaje": "Agente iniciado"}
        
        elif control.accion == "pausar":
            # En MVP, simplemente cambiar estado
            return {"mensaje": "Agente pausado"}
        
        elif control.accion == "reanudar":
            asyncio.create_task(agente.ejecutar_ciclo())
            return {"mensaje": "Agente reanudado"}
        
        else:
            raise HTTPException(status_code=400, detail="Acción no válida")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket para logs en tiempo real
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket para transmitir logs en tiempo real"""
    await manager.connect(websocket)
    
    # Registrar callbacks en el agente
    async def callback_log(log_data):
        await manager.broadcast({
            "tipo": "log",
            "data": log_data
        })
    
    async def callback_estado(estado_data):
        await manager.broadcast({
            "tipo": "estado",
            "data": estado_data
        })
    
    agente.registrar_callback_log(callback_log)
    agente.registrar_callback_estado(callback_estado)
    
    try:
        while True:
            # Mantener conexión abierta
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error en WebSocket: {e}")
        manager.disconnect(websocket)


# Servir archivos estáticos del frontend
@app.get("/")
async def root():
    """Servir la aplicación frontend"""
    return FileResponse("static/index.html")


# Montar archivos estáticos
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"Advertencia: No se pudo montar archivos estáticos: {e}")


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Ejecutar al iniciar la aplicación"""
    print("🚀 AutomataAI iniciado")
    print(f"📊 Base de datos: {DATABASE_URL}")
    print(f"🧠 Ollama: {OLLAMA_BASE_URL}")
    
    # Iniciar el ciclo del agente
    asyncio.create_task(agente_loop())


async def agente_loop():
    """Bucle principal del agente"""
    while True:
        try:
            print("\n⚙️  Iniciando ciclo del agente...")
            await agente.ejecutar_ciclo()
            print("✅ Ciclo completado")
            
            # Esperar antes del próximo ciclo (5 minutos en MVP)
            await asyncio.sleep(300)
        
        except Exception as e:
            print(f"❌ Error en bucle del agente: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
