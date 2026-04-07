"""
LLM-based Supervisor Brain using Ollama.
Analyzes UAE logs and suggests autonomous actions.
"""

from __future__ import annotations

import httpx
import logging
import os
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SupervisorBrain:
    def __init__(self) -> None:
        self.ollama_url = os.getenv("OLLAMA_URL", "http://163.192.114.190:11435")
        self.model = os.getenv("SUPERVISOR_MODEL", "deepseek-coder:6.7b")
        logger.info("SupervisorBrain initialized with Ollama: %s | Model: %s", self.ollama_url, self.model)

    async def analyze_log(self, uae_id: str, log_msg: str) -> Dict[str, Any]:
        """
        Send a log message to Ollama for analysis.
        Returns a dict with 'action', 'severity', and 'insight'.
        """
        system_prompt = (
            "Eres el Cerebro Supervisor de un ecosistema de agentes autónomos (UAE). "
            "Tu trabajo es vigilar los logs de los agentes y detectar: "
            "1. Errores críticos. 2. Ganancias confirmadas ($). 3. Sugerencias de mitosis. "
            "Responde SIEMPRE en formato JSON puro con estas llaves: "
            "{"
            "  \"severity\": \"INFO\" | \"WARNING\" | \"CRITICAL\","
            "  \"action\": \"NONE\" | \"ALERT\" | \"REBALANCE\" | \"STOP_UAE\" | \"MITOSIS\","
            "  \"insight\": \"Breve explicación útil para el usuario\""
            "}"
        )
        
        user_prompt = f"Agent: {uae_id}\nLog: {log_msg}\n\nAnaliza y responde en JSON:"
        
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "format": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "{}")
                return json.loads(response_text)
        except Exception as exc:
            logger.warning("SupervisorBrain (Ollama) failed: %s", exc)
            return {"severity": "INFO", "action": "NONE", "insight": "Error consultando al cerebro supervisor."}
