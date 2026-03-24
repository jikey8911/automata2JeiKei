import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import os

from puertos.financiero import IServicioFinanciero, Transaccion

logger = logging.getLogger(__name__)


class BinanceAdapter(IServicioFinanciero):
    """Adaptador para Binance API - Pagos y transferencias"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True
    ):
        # Cargar credenciales desde variables de entorno
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.testnet = testnet
        
        self.conectado = False
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        
        # En MVP, simulamos el cliente
        # En producción: from binance.client import Client
        self.client = None
        
        logger.info(f"BinanceAdapter inicializado (testnet={testnet})")
    
    async def conectar(self) -> bool:
        """Conectar con Binance API"""
        try:
            if not self.api_key or not self.api_secret:
                logger.warning("⚠️ Credenciales de Binance no configuradas")
                logger.info("Para usar Binance, configura: BINANCE_API_KEY y BINANCE_API_SECRET")
                return False
            
            logger.info(f"Conectando a Binance ({self.base_url})")
            
            # En producción:
            # from binance.client import Client
            # self.client = Client(self.api_key, self.api_secret)
            # self.client.ping()
            
            # MVP: simulación
            self.conectado = True
            logger.info("✅ Conectado a Binance")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error conectando a Binance: {e}")
            return False
    
    async def desconectar(self) -> bool:
        """Desconectar de Binance"""
        try:
            self.conectado = False
            logger.info("✅ Desconectado de Binance")
            return True
        except Exception as e:
            logger.error(f"❌ Error desconectando: {e}")
            return False
    
    async def consultar_balance(self, simbolo: str = "USDT") -> float:
        """Consultar balance de una moneda"""
        try:
            if not self.conectado:
                logger.warning("No conectado a Binance")
                return 0.0
            
            logger.info(f"Consultando balance de {simbolo}")
            
            # En producción:
            # account = self.client.get_account()
            # for balance in account['balances']:
            #     if balance['asset'] == simbolo:
            #         return float(balance['free'])
            
            # MVP: retornar balance simulado
            return 1234.56  # Simulado
        
        except Exception as e:
            logger.error(f"❌ Error consultando balance: {e}")
            return 0.0
    
    async def enviar_usdt(self, direccion_destino: str, monto: float) -> Dict[str, Any]:
        """Enviar USDT a una dirección"""
        try:
            if not self.conectado:
                return {"exitoso": False, "error": "No conectado"}
            
            # Validar dirección
            if not await self.validar_direccion(direccion_destino):
                return {"exitoso": False, "error": "Dirección inválida"}
            
            # Validar monto
            if monto <= 0:
                return {"exitoso": False, "error": "Monto debe ser > 0"}
            
            # Consultar balance
            balance = await self.consultar_balance("USDT")
            if balance < monto:
                return {
                    "exitoso": False,
                    "error": f"Balance insuficiente. Disponible: {balance} USDT"
                }
            
            logger.info(f"Enviando {monto} USDT a {direccion_destino}")
            
            # En producción:
            # result = self.client.withdraw(
            #     coin='USDT',
            #     withdrawOrderId=None,
            #     network='TRX',  # Red TRON para USDT
            #     address=direccion_destino,
            #     amount=monto,
            #     transactionFeeFlag=True,
            #     name=None
            # )
            
            # MVP: simulación
            hash_transaccion = f"0x{'a' * 64}"
            
            logger.info(f"✅ Transacción iniciada: {hash_transaccion}")
            
            return {
                "exitoso": True,
                "hash_transaccion": hash_transaccion,
                "monto": monto,
                "simbolo": "USDT",
                "direccion_destino": direccion_destino,
                "estado": "pendiente",
                "timestamp": datetime.now().isoformat(),
                "comisión": await self.obtener_comisión_estimada(monto)
            }
        
        except Exception as e:
            logger.error(f"❌ Error enviando USDT: {e}")
            return {"exitoso": False, "error": str(e)}
    
    async def obtener_historial_transacciones(
        self,
        limite: int = 50,
        offset: int = 0
    ) -> List[Transaccion]:
        """Obtener historial de transacciones"""
        try:
            if not self.conectado:
                return []
            
            logger.info(f"Obteniendo historial (límite: {limite}, offset: {offset})")
            
            # En producción:
            # deposits = self.client.get_deposit_history()
            # withdraws = self.client.get_withdraw_history()
            
            # MVP: retornar lista vacía o simulada
            transacciones = [
                Transaccion(
                    id=f"tx_{i}",
                    monto=100.0 + i * 10,
                    simbolo="USDT",
                    tipo="envio",
                    fecha=datetime.now(),
                    estado="completada",
                    direccion_destino="0x..." + str(i),
                    comisión=2.0
                )
                for i in range(min(5, limite))
            ]
            
            return transacciones
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial: {e}")
            return []
    
    async def obtener_tasa_cambio(self, simbolo: str = "USDT") -> Dict[str, float]:
        """Obtener tasa de cambio actual"""
        try:
            if not self.conectado:
                return {}
            
            logger.info(f"Obteniendo tasa de cambio para {simbolo}")
            
            # En producción:
            # ticker = self.client.get_symbol_ticker(symbol='USDTUSDT')
            # return {'USDT': float(ticker['price'])}
            
            # MVP: retornar tasas simuladas
            return {
                "USDT": 1.0,
                "USD": 1.0,
                "COP": 3800.0,  # Pesos colombianos
                "ARS": 850.0    # Pesos argentinos
            }
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo tasa: {e}")
            return {}
    
    async def validar_direccion(self, direccion: str) -> bool:
        """Validar que una dirección sea válida"""
        try:
            # Validación básica
            if not direccion or len(direccion) < 20:
                return False
            
            # Para USDT en TRON, dirección comienza con T
            if direccion.startswith("T") and len(direccion) == 34:
                return True
            
            # Para Ethereum, dirección comienza con 0x
            if direccion.startswith("0x") and len(direccion) == 42:
                return True
            
            logger.warning(f"Dirección inválida: {direccion}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Error validando dirección: {e}")
            return False
    
    async def obtener_comisión_estimada(self, monto: float) -> float:
        """Obtener comisión estimada para una transacción"""
        try:
            # Comisión típica de Binance: 0.2% - 1%
            # Para MVP: 0.5%
            comisión = monto * 0.005
            logger.info(f"Comisión estimada: {comisión} USDT")
            return comisión
        
        except Exception as e:
            logger.error(f"❌ Error calculando comisión: {e}")
            return 0.0
    
    async def obtener_estado_transaccion(self, hash_transaccion: str) -> Dict[str, Any]:
        """Obtener estado de una transacción específica"""
        try:
            if not self.conectado:
                return {"error": "No conectado"}
            
            logger.info(f"Consultando estado de transacción: {hash_transaccion}")
            
            # En producción:
            # status = self.client.get_withdraw_history(txid=hash_transaccion)
            
            # MVP: retornar estado simulado
            return {
                "hash": hash_transaccion,
                "estado": "completada",
                "confirmaciones": 6,
                "monto": 100.0,
                "comisión": 2.0,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {"error": str(e)}
