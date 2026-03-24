from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaccion:
    """Representa una transacción financiera"""
    id: str
    monto: float
    simbolo: str
    tipo: str  # "envio", "recepcion", "compra", "venta"
    fecha: datetime
    estado: str  # "pendiente", "completada", "fallida"
    direccion_destino: Optional[str] = None
    hash_transaccion: Optional[str] = None
    comisión: float = 0.0
    descripción: str = ""


class IServicioFinanciero(ABC):
    """Puerto para servicios financieros y pagos"""
    
    @abstractmethod
    async def conectar(self) -> bool:
        """Conectar con el servicio financiero"""
        pass
    
    @abstractmethod
    async def desconectar(self) -> bool:
        """Desconectar del servicio"""
        pass
    
    @abstractmethod
    async def consultar_balance(self, simbolo: str = "USDT") -> float:
        """Consultar balance de una moneda"""
        pass
    
    @abstractmethod
    async def enviar_usdt(self, direccion_destino: str, monto: float) -> Dict[str, Any]:
        """Enviar USDT a una dirección"""
        pass
    
    @abstractmethod
    async def obtener_historial_transacciones(
        self,
        limite: int = 50,
        offset: int = 0
    ) -> List[Transaccion]:
        """Obtener historial de transacciones"""
        pass
    
    @abstractmethod
    async def obtener_tasa_cambio(self, simbolo: str = "USDT") -> Dict[str, float]:
        """Obtener tasa de cambio actual"""
        pass
    
    @abstractmethod
    async def validar_direccion(self, direccion: str) -> bool:
        """Validar que una dirección sea válida"""
        pass
    
    @abstractmethod
    async def obtener_comisión_estimada(self, monto: float) -> float:
        """Obtener comisión estimada para una transacción"""
        pass
    
    @abstractmethod
    async def obtener_estado_transaccion(self, hash_transaccion: str) -> Dict[str, Any]:
        """Obtener estado de una transacción específica"""
        pass
