from typing import List, Dict, Any
from datetime import datetime


class ConocimientoItem:
    """Representa un ítem de conocimiento aprendido por la IA"""
    def __init__(
        self,
        tipo: str,  # 'nicho_rentable', 'error_comun', 'herramienta_util', 'estrategia_exitosa', 'tendencia'
        contenido: Dict[str, Any],
        relevancia: float = 0.5,
        fecha_aprendizaje: datetime = None
    ):
        self.tipo = tipo
        self.contenido = contenido
        self.relevancia = relevancia
        self.fecha_aprendizaje = fecha_aprendizaje or datetime.now()
        self.contador_uso = 0


class BaseDeConocimiento:
    """Almacena y gestiona el conocimiento aprendido por la IA"""
    
    def __init__(self):
        self.items: List[ConocimientoItem] = []
    
    def agregar_conocimiento(
        self,
        tipo: str,
        contenido: Dict[str, Any],
        relevancia: float = 0.5
    ) -> None:
        """Agregar un nuevo conocimiento"""
        item = ConocimientoItem(tipo, contenido, relevancia)
        self.items.append(item)
    
    def obtener_por_tipo(self, tipo: str) -> List[ConocimientoItem]:
        """Obtener todos los conocimientos de un tipo específico"""
        return [item for item in self.items if item.tipo == tipo]
    
    def obtener_mas_relevante(self, tipo: str, limite: int = 5) -> List[ConocimientoItem]:
        """Obtener los conocimientos más relevantes de un tipo"""
        items = self.obtener_por_tipo(tipo)
        return sorted(items, key=lambda x: x.relevancia, reverse=True)[:limite]
    
    def incrementar_uso(self, indice: int) -> None:
        """Incrementar el contador de uso de un conocimiento"""
        if 0 <= indice < len(self.items):
            self.items[indice].contador_uso += 1
    
    def actualizar_relevancia(self, indice: int, nueva_relevancia: float) -> None:
        """Actualizar la relevancia de un conocimiento"""
        if 0 <= indice < len(self.items):
            self.items[indice].relevancia = min(1.0, max(0.0, nueva_relevancia))
