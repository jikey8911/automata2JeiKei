from abc import ABC, abstractmethod
from typing import Optional


class IGeneradorDeLenguaje(ABC):
    """Puerto para generación de texto y razonamiento con LLMs"""
    
    @abstractmethod
    async def generar_texto(
        self,
        prompt: str,
        modelo_preferido: str = "phi-3",
        temperatura: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generar texto usando un LLM local"""
        pass
    
    @abstractmethod
    async def analizar_sentimiento(self, texto: str) -> dict:
        """Analizar el sentimiento de un texto"""
        pass
    
    @abstractmethod
    async def extraer_entidades(self, texto: str) -> dict:
        """Extraer entidades nombradas de un texto"""
        pass
    
    @abstractmethod
    async def generar_hipotesis(
        self,
        contexto: str,
        conocimiento_previo: str = ""
    ) -> dict:
        """Generar una hipótesis de negocio basada en contexto"""
        pass
    
    @abstractmethod
    async def evaluar_viabilidad(
        self,
        estrategia: str,
        restricciones: str = ""
    ) -> dict:
        """Evaluar la viabilidad de una estrategia"""
        pass
