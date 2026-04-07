from __future__ import annotations

import logging
from typing import List, Dict

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)

class ResearchTool:
    def __init__(self, max_results: int = 5) -> None:
        # Subimos un poco los resultados (ej. de 3 a 5) para darle más variedad al agente
        self.max_results = max_results

    def search(self, query: str) -> List[Dict]:
        """Ejecuta la búsqueda web exacta en DuckDuckGo."""
        logger.info("Buscando oportunidad: '%s'", query)
        try:
            with DDGS() as ddgs:
                # Retorna un diccionario con 'title', 'href' y 'body'
                hits = list(ddgs.text(query, max_results=self.max_results))
                return hits
        except Exception as exc:
            logger.warning("Fallo en la búsqueda para '%s': %s", query, exc)
            return []

    def find_opportunity(self, agent_query: str) -> Dict:
        """
        El agente DEBE proporcionar el 'agent_query' basado en su propio 
        razonamiento y en los resultados de búsquedas anteriores.
        """
        if not agent_query:
            return {"error": "El agente no proporcionó una consulta de búsqueda."}

        results = self.search(agent_query)
        
        if results:
            return {
                "status": "success",
                "query_used": agent_query,
                "leads_found": len(results),
                "leads": results  # Le pasamos todos los resultados para que elija el mejor
            }
            
        return {
            "status": "no_results", 
            "query_used": agent_query, 
            "leads": []
        }