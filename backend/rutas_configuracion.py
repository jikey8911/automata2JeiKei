"""
Rutas de configuración del sistema
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os

router = APIRouter(prefix="/api", tags=["configuracion"])

# Almacenamiento simple de configuración (en producción usar BD)
CONFIG_FILE = "/tmp/automata_config.json"

class ConfigBinance(BaseModel):
    api_key: str
    api_secret: str
    address: str
    testnet: bool = False


def cargar_configuracion():
    """Cargar configuración desde archivo"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def guardar_configuracion(config: dict):
    """Guardar configuración en archivo"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False


@router.post("/configurar/binance")
async def configurar_binance(config: ConfigBinance):
    """Configurar credenciales de Binance"""
    try:
        # Validar que no esté vacío
        if not config.api_key or not config.api_secret or not config.address:
            raise HTTPException(status_code=400, detail="Todos los campos son requeridos")
        
        # Validar dirección (básico)
        if len(config.address) < 26:
            raise HTTPException(status_code=400, detail="Dirección inválida")
        
        # Cargar configuración actual
        configuracion = cargar_configuracion()
        
        # Actualizar Binance config
        configuracion['binance'] = {
            'api_key': config.api_key,
            'api_secret': config.api_secret,
            'address': config.address,
            'testnet': config.testnet
        }
        
        # Guardar
        if guardar_configuracion(configuracion):
            return {
                "status": "success",
                "mensaje": "Configuración de Binance guardada correctamente",
                "testnet": config.testnet
            }
        else:
            raise HTTPException(status_code=500, detail="Error al guardar configuración")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configurar/binance/status")
async def obtener_status_binance():
    """Obtener estado de configuración de Binance"""
    try:
        config = cargar_configuracion()
        binance_config = config.get('binance', {})
        
        return {
            "configurado": bool(binance_config),
            "testnet": binance_config.get('testnet', False),
            "address": binance_config.get('address', '')[:10] + '...' if binance_config.get('address') else 'No configurada'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sistema/info")
async def obtener_info_sistema():
    """Obtener información general del sistema"""
    return {
        "nombre": "AutomataAI",
        "version": "2.0.0",
        "estado": "operativo",
        "features": ["ollama", "appium", "binance", "websocket", "postgresql"]
    }
