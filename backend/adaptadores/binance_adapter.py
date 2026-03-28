import logging
import random
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from binance.client import Client
from binance.exceptions import BinanceAPIException

from puertos.financiero import IServicioFinanciero, Transaccion

logger = logging.getLogger(__name__)

class BinanceAdapter(IServicioFinanciero):
    """Adaptador para Binance API - Pagos y transferencias reales"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True
    ):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.testnet = testnet
        self.client: Optional[Client] = None
        self.conectado = False
        
        logger.info(f"BinanceAdapter inicializado (testnet={testnet})")
    
    async def conectar(self) -> bool:
        """Conectar con la API real de Binance"""
        try:
            if not self.api_key or not self.api_secret:
                logger.warning("⚠️ Credenciales de Binance no configuradas.")
                return False
            
            # Inicializar cliente de Binance
            self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
            
            # Verificar conexión con un ping
            self.client.ping()
            self.conectado = True
            
            logger.info(f"✅ Conectado a Binance {'Testnet' if self.testnet else 'Mainnet'}")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a Binance: {e}")
            self.conectado = False
            return False
            
    async def consultar_balance(self, simbolo: str = "USDT") -> float:
        """Consultar balance real en la cuenta"""
        if not self.conectado or not self.client:
            await self.conectar()
            
        if not self.conectado:
            return 0.0
            
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == simbolo:
                    return float(balance['free'])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Error consultando balance: {e}")
            return 0.0

    async def enviar_usdt(self, direccion_destino: str, monto: float) -> Dict[str, Any]:
        """Realizar una transferencia real de USDT"""
        if not self.conectado or not self.client:
            if not await self.conectar():
                return {"exitoso": False, "error": "No conectado"}

        try:
            # En Testnet, los retiros suelen estar deshabilitados o simulados.
            # En producción, esto envía fondos reales.
            result = self.client.withdraw(
                coin='USDT',
                network='TRX',  # Red TRON sugerida por bajas comisiones
                address=direccion_destino,
                amount=monto
            )
            
            return {
                "exitoso": True,
                "id_transferencia": result.get('id', 'N/A'),
                "monto": monto,
                "timestamp": datetime.now().isoformat()
            }
        except BinanceAPIException as e:
            logger.error(f"❌ Error en transferencia Binance: {e}")
            return {"exitoso": False, "error": str(e)}

    async def obtener_tasa_cambio(self, simbolo: str = "USDT") -> Dict[str, float]:
        """Obtener precios del mercado en tiempo real"""
        if not self.conectado or not self.client:
            await self.conectar()
            
        try:
            # Ejemplo: USDT a BTC, ETH, etc.
            prices = self.client.get_all_tickers()
            relevant_prices = {}
            for p in prices:
                if p['symbol'] in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
                    relevant_prices[p['symbol']] = float(p['price'])
            return relevant_prices
        except Exception:
            return {"USDT": 1.0}

    # Métodos de compatibilidad con la interfaz
    async def desconectar(self) -> bool:
        self.conectado = False
        self.client = None
        return True

    async def obtener_historial_transacciones(self, limite: int = 50, offset: int = 0) -> List[Transaccion]:
        # Implementación simplificada para el dashboard
        return []
        
    async def validar_direccion(self, direccion: str) -> bool:
        return len(direccion) > 20 and (direccion.startswith('T') or direccion.startswith('0x'))

    async def obtener_comisión_estimada(self, monto: float) -> float:
        """Obtener comisión estimada para una transacción (USDT-TRC20)"""
        # Basado en tarifas estándar de Binance para TRC20
        return 1.0

    async def obtener_estado_transaccion(self, hash_transaccion: str) -> Dict[str, Any]:
        """Obtener estado de una transacción específica (retiro)"""
        if not self.conectado or not self.client:
            if not await self.conectar():
                return {"estado": "error", "error": "No hay conexión con Binance"}
            
        try:
            # Intenta buscar en el historial de retiros. 
            # Binance permite filtrar por txId o el ID de retiro.
            withdraws = self.client.get_withdraw_history()
            for w in withdraws:
                if w.get('id') == hash_transaccion or w.get('txId') == hash_transaccion:
                    # Mapeo de estados de Binance:
                    # 0:Email Sent, 1:Cancelled, 2:Awaiting Approval, 3:Rejected, 4:Processing, 5:Failure, 6:Completed
                    status_map = {
                        0: "pendiente",
                        1: "fallida",
                        2: "pendiente",
                        3: "fallida",
                        4: "pendiente",
                        5: "fallida",
                        6: "completada"
                    }
                    return {
                        "exitoso": True,
                        "id": w.get('id'),
                        "hash": w.get('txId'),
                        "estado": status_map.get(w.get('status'), "desconocido"),
                        "monto": float(w.get('amount', 0)),
                        "timestamp": w.get('applyTime')
                    }
            return {"exitoso": False, "estado": "no_encontrada", "error": "Transacción no hallada en el historial reciente"}
        except Exception as e:
            logger.error(f"Error consultando estado de transacción: {e}")
            return {"exitoso": False, "estado": "error", "error": str(e)}
