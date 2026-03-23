from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ModeloIngresos:
    """Representación de un modelo de ingresos (experimento)"""
    def __init__(
        self,
        id: UUID,
        estrategia_nombre: str,
        estado: str,
        ingresos_generados: float = 0.0,
        fecha_creacion: datetime = None,
        datos_metricas: Dict[str, Any] = None,
        descripcion: str = "",
        plan_ejecucion: Dict[str, Any] = None,
        modelo_padre_id: Optional[UUID] = None
    ):
        self.id = id
        self.estrategia_nombre = estrategia_nombre
        self.estado = estado  # 'activo', 'exitoso', 'fallido', 'duplicado'
        self.ingresos_generados = ingresos_generados
        self.fecha_creacion = fecha_creacion or datetime.now()
        self.datos_metricas = datos_metricas or {}
        self.descripcion = descripcion
        self.plan_ejecucion = plan_ejecucion or {}
        self.modelo_padre_id = modelo_padre_id


class IRepositorio(ABC):
    """Puerto para persistencia de datos"""
    
    @abstractmethod
    async def guardar_modelo(self, modelo: ModeloIngresos) -> None:
        """Guardar un modelo de ingresos en la base de datos"""
        pass
    
    @abstractmethod
    async def actualizar_estado_modelo(self, modelo_id: UUID, nuevo_estado: str) -> None:
        """Actualizar el estado de un modelo"""
        pass
    
    @abstractmethod
    async def obtener_modelo(self, modelo_id: UUID) -> Optional[ModeloIngresos]:
        """Obtener un modelo por ID"""
        pass
    
    @abstractmethod
    async def obtener_todos_modelos(self, estado: Optional[str] = None) -> List[ModeloIngresos]:
        """Obtener todos los modelos, opcionalmente filtrados por estado"""
        pass
    
    @abstractmethod
    async def actualizar_ingresos_modelo(self, modelo_id: UUID, ingresos: float) -> None:
        """Actualizar los ingresos de un modelo"""
        pass
    
    @abstractmethod
    async def guardar_conocimiento(self, tipo: str, contenido: Dict[str, Any], relevancia: float = 0.5) -> None:
        """Guardar un nuevo conocimiento en la base de conocimiento"""
        pass
    
    @abstractmethod
    async def obtener_conocimiento(self, tipo: str) -> List[Dict[str, Any]]:
        """Obtener conocimiento por tipo"""
        pass
    
    @abstractmethod
    async def guardar_log_decision(
        self,
        estado_agente: str,
        prompt_enviado: str,
        respuesta_recibida: str,
        decision_tomada: str,
        modelo_id: Optional[UUID] = None,
        nivel_confianza: float = 0.5
    ) -> None:
        """Guardar un log de decisión de la IA"""
        pass
    
    @abstractmethod
    async def obtener_estado_agente(self) -> Dict[str, Any]:
        """Obtener el estado actual del agente"""
        pass
    
    @abstractmethod
    async def actualizar_estado_agente(self, datos: Dict[str, Any]) -> None:
        """Actualizar el estado del agente"""
        pass
