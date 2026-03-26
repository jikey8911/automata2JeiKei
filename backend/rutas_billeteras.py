"""
Rutas API para gestión de billeteras (Binance y Comodolar)
Endpoints para configurar, consultar y realizar transacciones
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
import json
import os

from adaptadores.binance_real_adapter import BinanceRealAdapter
from adaptadores.comodolar_adapter import ComodolarAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billeteras", tags=["billeteras"])

# Modelos Pydantic
class ConfiguracionBinance(BaseModel):
    """Modelo para configuración de Binance"""
    api_key: str = Field(..., description="API Key de Binance")
    api_secret: str = Field(..., description="API Secret de Binance")
    testnet: bool = Field(default=False, description="Usar testnet")
    direccion_usdt: str = Field(..., description="Dirección para recibir USDT")
    red: str = Field(default="TRX", description="Red (TRX o ETH)")


class ConfiguracionComodolar(BaseModel):
    """Modelo para configuración de Comodolar"""
    api_key: str = Field(..., description="API Key de Comodolar")
    api_secret: str = Field(..., description="API Secret de Comodolar")
    sandbox: bool = Field(default=False, description="Usar sandbox")
    divisa_principal: str = Field(default="USD", description="Divisa principal")


class TransferenciaUSDT(BaseModel):
    """Modelo para transferencia de USDT"""
    monto: float = Field(..., gt=0, description="Monto a enviar")
    direccion: str = Field(..., description="Dirección destino")
    red: str = Field(default="TRX", description="Red (TRX o ETH)")


class TransferenciaComodolar(BaseModel):
    """Modelo para transferencia Comodolar"""
    monto: float = Field(..., gt=0, description="Monto a enviar")
    divisa: str = Field(..., description="Divisa (USD, COP)")
    numero_cuenta: str = Field(..., description="Número de cuenta destino")
    banco: str = Field(..., description="Código del banco")
    tipo_cuenta: str = Field(default="ahorros", description="Tipo de cuenta")


class ConversionDivisas(BaseModel):
    """Modelo para conversión de divisas"""
    monto: float = Field(..., gt=0, description="Monto a convertir")
    divisa_origen: str = Field(..., description="Divisa origen")
    divisa_destino: str = Field(..., description="Divisa destino")


# Variables globales para adaptadores
binance_adapter: Optional[BinanceRealAdapter] = None
comodolar_adapter: Optional[ComodolarAdapter] = None

CONFIG_FILE = "/tmp/billeteras_config.json"


def cargar_configuracion() -> Dict[str, Any]:
    """Cargar configuración de billeteras"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def guardar_configuracion(config: Dict[str, Any]):
    """Guardar configuración de billeteras"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")


def inicializar_adaptadores():
    """Inicializar adaptadores con configuración guardada"""
    global binance_adapter, comodolar_adapter
    
    config = cargar_configuracion()
    
    # Inicializar Binance
    if 'binance' in config:
        try:
            binance_config = config['binance']
            binance_adapter = BinanceRealAdapter(
                api_key=binance_config['api_key'],
                api_secret=binance_config['api_secret'],
                testnet=binance_config.get('testnet', False)
            )
            logger.info("Binance adapter inicializado")
        except Exception as e:
            logger.error(f"Error inicializando Binance: {e}")
    
    # Inicializar Comodolar
    if 'comodolar' in config:
        try:
            comodolar_config = config['comodolar']
            comodolar_adapter = ComodolarAdapter(
                api_key=comodolar_config['api_key'],
                api_secret=comodolar_config['api_secret'],
                sandbox=comodolar_config.get('sandbox', False)
            )
            logger.info("Comodolar adapter inicializado")
        except Exception as e:
            logger.error(f"Error inicializando Comodolar: {e}")


# ============================================================================
# ENDPOINTS BINANCE
# ============================================================================

@router.post("/binance/configurar")
async def configurar_binance(config: ConfiguracionBinance):
    """
    Configurar credenciales de Binance
    
    Args:
        config: Configuración de Binance
    
    Returns:
        Confirmación de configuración
    """
    try:
        global binance_adapter
        
        # Crear adaptador
        binance_adapter = BinanceRealAdapter(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        
        # Validar credenciales
        await binance_adapter.obtener_info_cuenta()
        
        # Guardar configuración
        config_actual = cargar_configuracion()
        config_actual['binance'] = {
            'api_key': config.api_key,
            'api_secret': config.api_secret,
            'testnet': config.testnet,
            'direccion_usdt': config.direccion_usdt,
            'red': config.red
        }
        guardar_configuracion(config_actual)
        
        logger.info("Configuración de Binance guardada")
        
        return {
            'status': 'success',
            'mensaje': 'Binance configurado correctamente',
            'testnet': config.testnet
        }
    
    except Exception as e:
        logger.error(f"Error configurando Binance: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binance/balance")
async def obtener_balance_binance(simbolo: str = "USDT"):
    """
    Obtener balance de Binance
    
    Args:
        simbolo: Símbolo de la moneda
    
    Returns:
        Balance disponible
    """
    try:
        if not binance_adapter:
            raise HTTPException(status_code=400, detail="Binance no configurado")
        
        balance = await binance_adapter.obtener_balance(simbolo)
        
        return {
            'status': 'success',
            'simbolo': simbolo,
            'balance': balance
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo balance: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binance/balance-total")
async def obtener_balance_total_binance():
    """
    Obtener balance total en todas las monedas
    
    Returns:
        Diccionario con todos los balances
    """
    try:
        if not binance_adapter:
            raise HTTPException(status_code=400, detail="Binance no configurado")
        
        balances = await binance_adapter.obtener_balance_total()
        
        return {
            'status': 'success',
            'balances': balances
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo balances: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/binance/enviar-usdt")
async def enviar_usdt(transferencia: TransferenciaUSDT):
    """
    Enviar USDT a una dirección
    
    Args:
        transferencia: Datos de la transferencia
    
    Returns:
        Información de la transacción
    """
    try:
        if not binance_adapter:
            raise HTTPException(status_code=400, detail="Binance no configurado")
        
        resultado = await binance_adapter.enviar_usdt(
            direccion=transferencia.direccion,
            monto=transferencia.monto,
            network=transferencia.red
        )
        
        return resultado
    
    except Exception as e:
        logger.error(f"Error enviando USDT: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binance/historial")
async def obtener_historial_binance(limite: int = 50):
    """
    Obtener historial de transacciones de Binance
    
    Args:
        limite: Número máximo de transacciones
    
    Returns:
        Lista de transacciones
    """
    try:
        if not binance_adapter:
            raise HTTPException(status_code=400, detail="Binance no configurado")
        
        historial = await binance_adapter.obtener_historial_transacciones(limite)
        
        return {
            'status': 'success',
            'total': len(historial),
            'transacciones': historial
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binance/tasa-cambio")
async def obtener_tasa_binance(simbolo: str = "USDT"):
    """
    Obtener tasa de cambio de Binance
    
    Args:
        simbolo: Símbolo de la moneda
    
    Returns:
        Información de tasa
    """
    try:
        if not binance_adapter:
            raise HTTPException(status_code=400, detail="Binance no configurado")
        
        tasa = await binance_adapter.obtener_tasa_cambio(simbolo)
        
        return {
            'status': 'success',
            'tasa': tasa
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo tasa: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ENDPOINTS COMODOLAR
# ============================================================================

@router.post("/comodolar/configurar")
async def configurar_comodolar(config: ConfiguracionComodolar):
    """
    Configurar credenciales de Comodolar
    
    Args:
        config: Configuración de Comodolar
    
    Returns:
        Confirmación de configuración
    """
    try:
        global comodolar_adapter
        
        # Crear adaptador
        comodolar_adapter = ComodolarAdapter(
            api_key=config.api_key,
            api_secret=config.api_secret,
            sandbox=config.sandbox
        )
        
        # Validar credenciales
        await comodolar_adapter.obtener_info_cuenta()
        
        # Guardar configuración
        config_actual = cargar_configuracion()
        config_actual['comodolar'] = {
            'api_key': config.api_key,
            'api_secret': config.api_secret,
            'sandbox': config.sandbox,
            'divisa_principal': config.divisa_principal
        }
        guardar_configuracion(config_actual)
        
        logger.info("Configuración de Comodolar guardada")
        
        return {
            'status': 'success',
            'mensaje': 'Comodolar configurado correctamente',
            'sandbox': config.sandbox
        }
    
    except Exception as e:
        logger.error(f"Error configurando Comodolar: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comodolar/balance")
async def obtener_balance_comodolar(divisa: str = "USD"):
    """
    Obtener balance de Comodolar
    
    Args:
        divisa: Código de divisa
    
    Returns:
        Balance disponible
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        balance = await comodolar_adapter.obtener_balance(divisa)
        
        return {
            'status': 'success',
            'divisa': divisa,
            'balance': balance
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo balance: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comodolar/balance-total")
async def obtener_balance_total_comodolar():
    """
    Obtener balance total en todas las divisas
    
    Returns:
        Diccionario con todos los balances
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        balances = await comodolar_adapter.obtener_balance_total()
        
        return {
            'status': 'success',
            'balances': balances
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo balances: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/comodolar/transferencia")
async def enviar_transferencia_comodolar(transferencia: TransferenciaComodolar):
    """
    Enviar dinero a una cuenta bancaria
    
    Args:
        transferencia: Datos de la transferencia
    
    Returns:
        Información de la transacción
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        resultado = await comodolar_adapter.enviar_transferencia(
            monto=transferencia.monto,
            divisa=transferencia.divisa,
            numero_cuenta=transferencia.numero_cuenta,
            banco=transferencia.banco,
            tipo_cuenta=transferencia.tipo_cuenta
        )
        
        return resultado
    
    except Exception as e:
        logger.error(f"Error enviando transferencia: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/comodolar/convertir")
async def convertir_divisas_comodolar(conversion: ConversionDivisas):
    """
    Convertir dinero entre divisas
    
    Args:
        conversion: Datos de conversión
    
    Returns:
        Resultado de conversión
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        resultado = await comodolar_adapter.convertir_divisas(
            monto=conversion.monto,
            divisa_origen=conversion.divisa_origen,
            divisa_destino=conversion.divisa_destino
        )
        
        return resultado
    
    except Exception as e:
        logger.error(f"Error en conversión: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comodolar/historial")
async def obtener_historial_comodolar(divisa: Optional[str] = None, limite: int = 50):
    """
    Obtener historial de transacciones
    
    Args:
        divisa: Filtrar por divisa (opcional)
        limite: Número máximo de transacciones
    
    Returns:
        Lista de transacciones
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        historial = await comodolar_adapter.obtener_historial_transacciones(
            divisa=divisa,
            limite=limite
        )
        
        return {
            'status': 'success',
            'total': len(historial),
            'transacciones': historial
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comodolar/tarjetas")
async def obtener_tarjetas_comodolar():
    """
    Obtener lista de tarjetas de débito
    
    Returns:
        Lista de tarjetas
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        tarjetas = await comodolar_adapter.obtener_tarjetas()
        
        return {
            'status': 'success',
            'total': len(tarjetas),
            'tarjetas': tarjetas
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo tarjetas: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comodolar/limites")
async def obtener_limites_comodolar():
    """
    Obtener límites de transacciones
    
    Returns:
        Información de límites
    """
    try:
        if not comodolar_adapter:
            raise HTTPException(status_code=400, detail="Comodolar no configurado")
        
        limites = await comodolar_adapter.obtener_limites()
        
        return {
            'status': 'success',
            'limites': limites
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo límites: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def obtener_estado_billeteras():
    """
    Obtener estado de las billeteras configuradas
    
    Returns:
        Estado de Binance y Comodolar
    """
    config = cargar_configuracion()
    
    return {
        'status': 'success',
        'binance_configurado': 'binance' in config,
        'comodolar_configurado': 'comodolar' in config,
        'binance_testnet': config.get('binance', {}).get('testnet', False),
        'comodolar_sandbox': config.get('comodolar', {}).get('sandbox', False)
    }


# Inicializar adaptadores al cargar el módulo
inicializar_adaptadores()
