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

class ConfigComodolar(BaseModel):
    api_key: str
    api_secret: str
    api_url: Optional[str] = 'http://dolarapp-backend:8000'

@router.post("/configurar/binance")
async def configurar_binance(config: ConfigBinance):
    """Configurar credenciales de Binance con persistencia en DB"""
    try:
        from main import repositorio
        
        await repositorio.guardar_configuracion_binance({
            'api_key': config.api_key,
            'api_secret': config.api_secret,
            'direccion_usdt': config.address,
            'testnet': config.testnet
        })
        
        return {
            "status": "success",
            "mensaje": "Configuración de Binance guardada de forma segura",
            "testnet": config.testnet
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configurar/comodolar")
async def configurar_comodolar(config: ConfigComodolar):
    """Configurar credenciales de Comodolar (DolarApp) con persistencia en DB"""
    try:
        from main import repositorio
        
        await repositorio.guardar_configuracion_comodolar({
            'api_key': config.api_key,
            'api_secret': config.api_secret,
            'api_url': config.api_url
        })
        
        return {
            "status": "success",
            "mensaje": "Configuración de DolarApp guardada de forma segura"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configurar/status")
async def obtener_status_configuracion():
    """Obtener estado de configuración de ambos servicios"""
    try:
        from main import repositorio
        
        binance = await repositorio.obtener_configuracion_binance()
        comodolar = await repositorio.obtener_configuracion_comodolar()
        
        return {
            "binance_configurado": bool(binance),
            "comodolar_configurado": bool(comodolar),
            "binance_testnet": binance.get('testnet', False) if binance else False,
            "binance_address": binance.get('direccion_usdt', '')[:10] + '...' if binance else 'No configurada'
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
        "features": ["ollama", "appium", "binance", "dolarapp", "postgresql"]
    }
