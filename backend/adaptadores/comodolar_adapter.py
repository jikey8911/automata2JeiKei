"""
Adaptador de Comodolar - Billetera de divisas
Maneja USD, COP y otras divisas con tarjeta de débito
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DivisaSoportada(Enum):
    """Divisas soportadas por Comodolar"""
    USD = "USD"
    COP = "COP"
    EUR = "EUR"
    MXN = "MXN"
    ARS = "ARS"


class TipoTransaccion(Enum):
    """Tipos de transacciones"""
    DEPOSITO = "deposito"
    RETIRO = "retiro"
    TRANSFERENCIA = "transferencia"
    COMPRA = "compra"


class ComodolarAdapter:
    """
    Adaptador para Comodolar - Billetera de divisas
    API: https://api.comodolar.com/v1
    """
    
    BASE_URL = "https://api.comodolar.com/v1"
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        """
        Inicializar cliente de Comodolar
        
        Args:
            api_key: API Key de Comodolar
            api_secret: API Secret de Comodolar
            sandbox: Si True, usa ambiente de prueba
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        
        if sandbox:
            self.base_url = "https://sandbox.comodolar.com/v1"
        else:
            self.base_url = self.BASE_URL
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Comodolar adapter inicializado (sandbox={sandbox})")
    
    async def obtener_balance(self, divisa: str = "USD") -> float:
        """
        Obtener balance en una divisa específica
        
        Args:
            divisa: Código de divisa (USD, COP, EUR)
        
        Returns:
            Balance disponible
        """
        try:
            response = self.session.get(
                f"{self.base_url}/wallet/balance",
                params={'currency': divisa}
            )
            response.raise_for_status()
            
            data = response.json()
            balance = float(data['balance'])
            
            logger.info(f"Balance {divisa}: {balance}")
            return balance
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo balance: {e}")
            raise
    
    async def obtener_balance_total(self) -> Dict[str, float]:
        """
        Obtener balance en todas las divisas
        
        Returns:
            Diccionario con balances por divisa
        """
        try:
            response = self.session.get(f"{self.base_url}/wallet/balances")
            response.raise_for_status()
            
            data = response.json()
            balances = {}
            
            for wallet in data['wallets']:
                balances[wallet['currency']] = float(wallet['balance'])
            
            logger.info(f"Balances totales obtenidos: {balances}")
            return balances
        
        except Exception as e:
            logger.error(f"Error obteniendo balances: {e}")
            raise
    
    async def enviar_transferencia(self, 
                                  monto: float,
                                  divisa: str,
                                  numero_cuenta: str,
                                  banco: str,
                                  tipo_cuenta: str = "ahorros") -> Dict[str, Any]:
        """
        Enviar dinero a una cuenta bancaria
        
        Args:
            monto: Cantidad a enviar
            divisa: Divisa (USD, COP)
            numero_cuenta: Número de cuenta destino
            banco: Código del banco
            tipo_cuenta: Tipo de cuenta (ahorros, corriente)
        
        Returns:
            Información de la transferencia
        """
        try:
            if monto <= 0:
                raise ValueError("Monto debe ser mayor a 0")
            
            payload = {
                'amount': monto,
                'currency': divisa,
                'account_number': numero_cuenta,
                'bank_code': banco,
                'account_type': tipo_cuenta,
                'description': f'Transferencia {divisa} {monto}'
            }
            
            response = self.session.post(
                f"{self.base_url}/transfers/send",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Transferencia exitosa: {data['transfer_id']}")
            
            return {
                'status': 'success',
                'transfer_id': data['transfer_id'],
                'monto': monto,
                'divisa': divisa,
                'cuenta_destino': numero_cuenta,
                'banco': banco,
                'estado': data['status'],
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error en transferencia: {e}")
            raise
    
    async def obtener_tasa_cambio(self, 
                                 divisa_origen: str = "USD",
                                 divisa_destino: str = "COP") -> Dict[str, Any]:
        """
        Obtener tasa de cambio entre dos divisas
        
        Args:
            divisa_origen: Divisa origen
            divisa_destino: Divisa destino
        
        Returns:
            Información de tasa de cambio
        """
        try:
            response = self.session.get(
                f"{self.base_url}/exchange-rates",
                params={
                    'from': divisa_origen,
                    'to': divisa_destino
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'divisa_origen': divisa_origen,
                'divisa_destino': divisa_destino,
                'tasa': float(data['rate']),
                'timestamp': data['timestamp']
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo tasa: {e}")
            raise
    
    async def convertir_divisas(self,
                               monto: float,
                               divisa_origen: str,
                               divisa_destino: str) -> Dict[str, Any]:
        """
        Convertir dinero entre divisas
        
        Args:
            monto: Cantidad a convertir
            divisa_origen: Divisa origen
            divisa_destino: Divisa destino
        
        Returns:
            Resultado de conversión
        """
        try:
            payload = {
                'amount': monto,
                'from_currency': divisa_origen,
                'to_currency': divisa_destino
            }
            
            response = self.session.post(
                f"{self.base_url}/exchange/convert",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Conversión: {monto} {divisa_origen} → {data['converted_amount']} {divisa_destino}")
            
            return {
                'monto_original': monto,
                'divisa_origen': divisa_origen,
                'monto_convertido': float(data['converted_amount']),
                'divisa_destino': divisa_destino,
                'tasa': float(data['rate']),
                'comision': float(data.get('fee', 0)),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error en conversión: {e}")
            raise
    
    async def obtener_historial_transacciones(self,
                                             divisa: Optional[str] = None,
                                             limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtener historial de transacciones
        
        Args:
            divisa: Filtrar por divisa (opcional)
            limite: Número máximo de transacciones
        
        Returns:
            Lista de transacciones
        """
        try:
            params = {'limit': limite}
            if divisa:
                params['currency'] = divisa
            
            response = self.session.get(
                f"{self.base_url}/transactions/history",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            transacciones = []
            
            for tx in data['transactions']:
                transacciones.append({
                    'id': tx['id'],
                    'tipo': tx['type'],
                    'monto': float(tx['amount']),
                    'divisa': tx['currency'],
                    'estado': tx['status'],
                    'descripcion': tx.get('description', ''),
                    'fecha': tx['timestamp'],
                    'referencia': tx.get('reference_id', '')
                })
            
            logger.info(f"Historial obtenido: {len(transacciones)} transacciones")
            return transacciones
        
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            raise
    
    async def obtener_tarjetas(self) -> List[Dict[str, Any]]:
        """
        Obtener lista de tarjetas de débito asociadas
        
        Returns:
            Lista de tarjetas
        """
        try:
            response = self.session.get(f"{self.base_url}/cards")
            response.raise_for_status()
            
            data = response.json()
            tarjetas = []
            
            for card in data['cards']:
                tarjetas.append({
                    'id': card['id'],
                    'ultimos_digitos': card['last_four'],
                    'marca': card['brand'],
                    'estado': card['status'],
                    'fecha_vencimiento': card['expiry_date'],
                    'divisa_principal': card['primary_currency']
                })
            
            logger.info(f"Tarjetas obtenidas: {len(tarjetas)}")
            return tarjetas
        
        except Exception as e:
            logger.error(f"Error obteniendo tarjetas: {e}")
            raise
    
    async def obtener_info_cuenta(self) -> Dict[str, Any]:
        """
        Obtener información de la cuenta
        
        Returns:
            Información de la cuenta
        """
        try:
            response = self.session.get(f"{self.base_url}/account/info")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'nombre': data['name'],
                'email': data['email'],
                'telefono': data.get('phone', ''),
                'pais': data['country'],
                'estado_verificacion': data['verification_status'],
                'fecha_creacion': data['created_at'],
                'divisas_soportadas': data.get('supported_currencies', [])
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo info: {e}")
            raise
    
    async def obtener_limites(self) -> Dict[str, Any]:
        """
        Obtener límites de transacciones
        
        Returns:
            Información de límites
        """
        try:
            response = self.session.get(f"{self.base_url}/account/limits")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'limite_diario': float(data['daily_limit']),
                'limite_mensual': float(data['monthly_limit']),
                'gastado_hoy': float(data['spent_today']),
                'gastado_mes': float(data['spent_this_month']),
                'disponible_hoy': float(data['available_today']),
                'disponible_mes': float(data['available_this_month'])
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo límites: {e}")
            raise
    
    async def obtener_tasas_comisiones(self) -> Dict[str, Any]:
        """
        Obtener tasas y comisiones actuales
        
        Returns:
            Información de tasas
        """
        try:
            response = self.session.get(f"{self.base_url}/fees")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'comision_transferencia': float(data['transfer_fee']),
                'comision_conversion': float(data['conversion_fee']),
                'comision_retiro': float(data['withdrawal_fee']),
                'comision_tarjeta': float(data.get('card_fee', 0)),
                'comision_deposito': float(data.get('deposit_fee', 0))
            }
        
        except Exception as e:
            logger.error(f"Error obteniendo tasas: {e}")
            raise
