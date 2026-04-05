"""
Agnostic research tool for digital profit opportunities using DuckDuckGo.
"""

from __future__ import annotations

import logging
import random
from typing import List, Dict

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)


BASE_QUERIES = [
    "high paying microtasks",
    "new api monetization",
    "emerging digital markets 2026",
    "automated income streams",
    "passive income api ideas",
    "ai agents freelance marketplaces new",
    "bug bounty new programs",
    "airdrop upcoming 2026",
    "seo arbitrage opportunities",
    "defi yield new pools",
]


class ResearchTool:
    def __init__(self, results: int = 3) -> None:
        self.results = results

    def _gen_query(self) -> str:
        return random.choice(BASE_QUERIES)

    def search(self, query: str) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=self.results))
                return hits
        except Exception as exc:
            logger.warning("Research failed for %s: %s", query, exc)
            return []

    def find_opportunity(self) -> Dict:
        query = self._gen_query()
        results = self.search(query)
        if results:
            return {"sector": "Unknown", "query": query, "lead": results[0]}
        return {"sector": "Unknown", "query": query, "lead": {}}
