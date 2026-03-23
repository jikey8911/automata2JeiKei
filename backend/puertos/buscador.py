from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ResultadoBusqueda:
    """Representación de un resultado de búsqueda"""
    def __init__(self, titulo: str, url: str, descripcion: str, relevancia: float = 0.5):
        self.titulo = titulo
        self.url = url
        self.descripcion = descripcion
        self.relevancia = relevancia


class IBuscadorWeb(ABC):
    """Puerto para búsqueda en internet"""
    
    @abstractmethod
    async def buscar(self, query: str, num_resultados: int = 10) -> List[ResultadoBusqueda]:
        """Buscar información en internet"""
        pass
    
    @abstractmethod
    async def buscar_tendencias(self, tema: str) -> List[Dict[str, Any]]:
        """Buscar tendencias sobre un tema específico"""
        pass
