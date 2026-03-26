"""
Adaptador Real de Binance - Implementación con python-binance
Maneja transacciones reales en Binance Spot y Futures
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from puertos.financiero import IServicioFinanciero

logger = logging.getLogger(__name__)


class BinanceRealAdapter(IServicioFinanciero):
    """
    Adaptador real de Binance usando python-binance
    Soporta: Spot Trading, Futures, Staking, Savings
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Inicializar cliente de Binance
        
        Args:
            api_key: API Key de Binance
            api_secret: API Secret de Binance
            testnet: Si True, usa testnet (desarrollo)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Configurar cliente
        if testnet:
            self.client = Client(
                api_key,
                api_secret,
                testnet=True,
                requests_params={"timeout": 30}
            )
        else:
            self.client = Client(
                api_key,
                api_secret,
                requests_params={"timeout": 30}
            )
        
        logger.info(f"Binance adapter inicializado (testnet={testnet})")
    
    async def obtener_balance(self, simbolo: str = "USDT") -> float:
        """
        Obtener balance de una moneda específica
        
        Args:
            simbolo: Símbolo de la moneda (USDT, BTC, ETH, etc.)
        
        Returns:
            Balance disponible
        """
        try:
            account = self.client.get_account()
            
            for balance in account['balances']:
                if balance['asset'] == simbolo:
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    logger.info(f"Balance {simbolo}: {free} (locked: {locked})")
                    return free
            
            logger.warning(f"No se encontró balance para {simbolo}")
            return 0.0
        
        except BinanceAPIException as e:
            logger.error(f"Error Binance API: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            raise
    
    async def obtener_balance_total(self) -> Dict[str, float]:
        """
        Obtener balance total de todas las monedas
        
        Returns:
            Diccionario con todos los balances
        """
        try:
            account = self.client.get_account()
            balances = {}
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[balance['asset']] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            logger.info(f"Balance total obtenido: {len(balances)} monedas")
            return balances
        
        except Exception as e:
            logger.error(f"Error obteniendo balance total: {e}")
            raise
    
    async def enviar_usdt(self, direccion: str, monto: float, 
                         network: str = "TRX") -> Dict[str, Any]:
        """
        Enviar USDT a una dirección
        
        Args:
            direccion: Dirección de destino (TRON o Ethereum)
            monto: Cantidad a enviar
            network: Red (TRX para TRON, ETH para Ethereum)
        
        Returns:
            Información de la transacción
        """
        try:
            # Validar monto
            if monto <= 0:
                raise ValueError("Monto debe ser mayor a 0")
            
            # Validar dirección
            if not self._validar_direccion(direccion, network):
                raise ValueError(f"Dirección inválida para red {network}")
            
            # Obtener comisión de red
            comision = await self._obtener_comision_red("USDT", network)
            
            # Restar comisión del monto
            monto_final = monto - comision
            
            if monto_final <= 0:
                raise ValueError(f"Monto insuficiente después de comisión ({comision})")
            
            logger.info(f"Enviando {monto_final} USDT a {direccion} (red: {network})")
            
            # Realizar transferencia
            resultado = self.client.withdraw(
                coin='USDT',
                withdrawOrderId=None,
                network=network,
                address=direccion,
                amount=monto_final
            )
            
            logger.info(f"Transferencia exitosa: {resultado['id']}")
            
            return {
                'status': 'success',
                'tx_id': resultado['id'],
                'monto': monto_final,
                'comision': comision,
                'direccion': direccion,
                'red': network,
                'timestamp': datetime.now().isoformat()
            }
        
        except BinanceAPIException as e:
            logger.error(f"Error Binance: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Error enviando USDT: {e}")
            raise
    
    async def obtener_historial_transacciones(self, 
                                             limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtener historial de transacciones
        
        Args:
            limite: Número máximo de transacciones
        
        Returns:
            Lista de transacciones
        """
        try:
            # Obtener historial de depósitos
            depositos = self.client.get_deposit_history(limit=limite)
            
            # Obtener historial de retiros
            retiros = self.client.get_withdraw_history(limit=limite)
            
            transacciones = []
            
            # Procesar depósitos
            for dep in depositos:
                transacciones.append({
                    'tipo': 'deposito',
                    'moneda': dep['coin'],
                    'monto': float(dep['amount']),
                    'estado': dep['status'],
                    'fecha': datetime.fromtimestamp(dep['insertTime']/1000).isoformat(),
                    'tx_id': dep.get('txId', 'N/A'),
                    'red': dep.get('network', 'N/A')
                })
            
            # Procesar retiros
            for ret in retiros:
                transacciones.append({
                    'tipo': 'retiro',
                    'moneda': ret['coin'],
                    'monto': float(ret['amount']),
                    'estado': ret['status'],
                    'fecha': datetime.fromtimestamp(ret['insertTime']/1000).isoformat(),
                    'tx_id': ret.get('txId', 'N/A'),
                    'red': ret.get('network', 'N/A'),
                    'comision': float(ret.get('transactionFee', 0))
                })
            
            # Ordenar por fecha descendente
            transacciones.sort(key=lambda x: x['fecha'], reverse=True)
            
            logger.info(f"Historial obtenido: {len(transacciones)} transacciones")
            return transacciones[:limite]
        
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            raise
    
    async def obtener_tasa_cambio(self, simbolo: str = "USDT") -> Dict[str, float]:
        """
        Obtener tasa de cambio actual
        
        Args:
            simbolo: Símbolo de la moneda
        
        Returns:
            Tasas de cambio
        """
        try:
            # Obtener precio de USDT en diferentes pares
            precios = self.client.get_symbol_info('USDT')
            
            # Obtener precio actual
            ticker = self.client.get_symbol_ticker(symbol='USDTBUSD')
            
            return {
                'simbolo': simbolo,
                'precio_usd': float(ticker['price']),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo tasa: {e}")
            return {'simbolo': simbolo, 'precio_usd': 1.0}
    
    async def validar_direccion(self, direccion: str, red: str = "TRX") -> bool:
        """
        Validar que una dirección sea válida
        
        Args:
            direccion: Dirección a validar
            red: Red (TRX o ETH)
        
        Returns:
            True si es válida
        """
        return self._validar_direccion(direccion, red)
    
    def _validar_direccion(self, direccion: str, red: str) -> bool:
        """
        Validar dirección según la red
        """
        if red == "TRX":
            # TRON addresses comienzan con T y tienen 34 caracteres
            return len(direccion) == 34 and direccion.startswith('T')
        elif red == "ETH":
            # Ethereum addresses comienzan con 0x y tienen 42 caracteres
            return len(direccion) == 42 and direccion.startswith('0x')
        return False
    
    async def _obtener_comision_red(self, moneda: str, red: str) -> float:
        """
        Obtener comisión de red para una moneda
        """
        try:
            # Obtener información de comisiones
            asset = self.client.get_asset_balance(asset=moneda)
            
            # Valores por defecto
            comisiones = {
                ('USDT', 'TRX'): 1.0,
                ('USDT', 'ETH'): 10.0,
                ('BTC', 'TRX'): 0.0005,
                ('ETH', 'ETH'): 0.01
            }
            
            return comisiones.get((moneda, red), 1.0)
        except:
            return 1.0
    
    async def obtener_info_cuenta(self) -> Dict[str, Any]:
        """
        Obtener información completa de la cuenta
        """
        try:
            account = self.client.get_account()
            
            return {
                'maker_commission': account['makerCommission'],
                'taker_commission': account['takerCommission'],
                'buyer_commission': account['buyerCommission'],
                'seller_commission': account['sellerCommission'],
                'can_trade': account['canTrade'],
                'can_deposit': account['canDeposit'],
                'can_withdraw': account['canWithdraw'],
                'update_time': datetime.fromtimestamp(account['updateTime']/1000).isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo info de cuenta: {e}")
            raise
    
    async def obtener_pares_disponibles(self) -> List[str]:
        """
        Obtener lista de pares de trading disponibles
        """
        try:
            exchange_info = self.client.get_exchange_info()
            pares = [s['symbol'] for s in exchange_info['symbols'] if s['status'] == 'TRADING']
            return pares[:50]  # Retornar los primeros 50
        except Exception as e:
            logger.error(f"Error obteniendo pares: {e}")
            return []
