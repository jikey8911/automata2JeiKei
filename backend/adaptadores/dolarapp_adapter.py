import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DolarAppAdapter:
    """Implementa la integración con DolarApp como sistema de respaldo (fallback)"""
    
    def __init__(self, repositorio, api_url: str = None):
        """
        Inicializar adaptador
        
        Args:
            repositorio: Instancia del repositorio (PostgresAdapter) para leer credenciales
            api_url: URL base de la API de DolarApp
        """
        self.repositorio = repositorio
        self._api_url_override = api_url

    async def _obtener_configuracion(self) -> Dict[str, Any]:
        """Obtener configuración de la base de datos"""
        config = await self.repositorio.obtener_configuracion_comodolar()
        if not config:
            return {}
        
        # Prioridad: 1. Override en constructor, 2. URL en BD, 3. Default
        if not self._api_url_override:
            self._api_url_override = config.get('api_url', 'http://dolarapp-backend:8000')
            
        return config

    async def enviar_fondos_respaldo(self, monto: float, referencia: str) -> Dict[str, Any]:
        """
        Envía fondos a DolarApp si Binance no está disponible.
        
        Args:
            monto: Cantidad de USDT a depositar
            referencia: Texto identificador de la transacción
        """
        config = await self._obtener_configuracion()
        if not config:
            logger.error("No se encontró configuración para DolarApp/Comodolar")
            return {"status": "error", "message": "Configuración no encontrada"}

        try:
            url = self._api_url_override
            headers = {
                "X-Api-Key": config['api_key'],
                "X-Api-Secret": config['api_secret'],
                "Content-Type": "application/json"
            }
            
            payload = {
                "wallet_id": 1, # ID por defecto para la billetera principal
                "monto": str(monto),
                "referencia": referencia,
                "token": "USDT"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"Enviando fallback a DolarApp: {monto} USDT (Ref: {referencia})")
                response = await client.post(f"{url}/api/depositos", json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info("Transferencia de respaldo exitosa en DolarApp")
                    return response.json()
                else:
                    logger.error(f"Error en DolarApp API: {response.status_code} - {response.text}")
                    return {"status": "error", "code": response.status_code, "message": response.text}
                    
        except Exception as e:
            logger.error(f"Excepción durante comunicación con DolarApp: {e}")
            return {"status": "error", "message": str(e)}

    async def verificar_salud(self) -> bool:
        """Verificar si el microservicio DolarApp está respondiendo"""
        try:
            config = await self._obtener_configuracion()
            url = self._api_url_override or "http://dolarapp-backend:8000"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/api/health")
                return response.status_code == 200
        except:
            return False
