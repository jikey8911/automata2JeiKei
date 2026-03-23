from typing import List, Dict, Any
from duckduckgo_search import DDGS

from puertos.buscador import IBuscadorWeb, ResultadoBusqueda


class DuckDuckGoAdapter(IBuscadorWeb):
    """Adaptador para búsqueda web usando DuckDuckGo (sin API key requerida)"""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    async def buscar(self, query: str, num_resultados: int = 10) -> List[ResultadoBusqueda]:
        """Buscar información en internet usando DuckDuckGo"""
        try:
            resultados = []
            
            # Realizar búsqueda
            search_results = self.ddgs.text(query, max_results=num_resultados)
            
            for i, result in enumerate(search_results):
                # Calcular relevancia basada en posición
                relevancia = 1.0 - (i / num_resultados)
                
                resultado = ResultadoBusqueda(
                    titulo=result.get('title', 'Sin título'),
                    url=result.get('href', ''),
                    descripcion=result.get('body', ''),
                    relevancia=relevancia
                )
                resultados.append(resultado)
            
            return resultados
        
        except Exception as e:
            print(f"Error en búsqueda DuckDuckGo: {e}")
            return []
    
    async def buscar_tendencias(self, tema: str) -> List[Dict[str, Any]]:
        """Buscar tendencias sobre un tema específico"""
        try:
            query = f"tendencias {tema} 2026"
            resultados = await self.buscar(query, num_resultados=5)
            
            return [
                {
                    "titulo": r.titulo,
                    "url": r.url,
                    "descripcion": r.descripcion,
                    "relevancia": r.relevancia
                }
                for r in resultados
            ]
        
        except Exception as e:
            print(f"Error al buscar tendencias: {e}")
            return []
