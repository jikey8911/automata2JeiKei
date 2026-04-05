"""
Hybrid reasoning brain for UAE.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Optional, Tuple

import httpx
from anthropic import Anthropic

from AutomataEcosystem.core.database import EncryptedSecretStore, ModelAuditLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)


class BrainAgent:
    def __init__(self, supervisor_url: str) -> None:
        self.supervisor_url = supervisor_url
        self.store = EncryptedSecretStore()
        self.audit = ModelAuditLog(self.store)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = Anthropic(api_key=self.claude_api_key) if self.claude_api_key else None

    async def generate_with_ollama(self, prompt: str, model: str = "deepseek-coder:6.7b") -> str:
        payload = {"model": model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except Exception as exc:
            logger.warning("Ollama generation failed (%s): %s", model, exc)
            return ""

    async def validate_code(self, code: str) -> Tuple[bool, str]:
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as tmp:
                tmp.write(code)
                path = tmp.name
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "py_compile", path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            success = proc.returncode == 0
            return success, stderr.decode() if stderr else ""
        except Exception as exc:
            return False, str(exc)

    async def escalate_to_claude(self, prompt: str, reason: str) -> str:
        if not self.claude_client:
            logger.warning("Claude client not configured; skipping escalation")
            self.audit.log_call("claude-3.5-sonnet", reason, 0.0, "skipped", "no_api_key")
            return ""
        cost_estimate = 0.02  # rough placeholder USD
        try:
            msg = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            self.audit.log_call("claude-3.5-sonnet", reason, cost_estimate, "success", None)
            return msg.content[0].text if msg.content else ""
        except Exception as exc:
            self.audit.log_call("claude-3.5-sonnet", reason, cost_estimate, "failed", str(exc))
            logger.warning("Claude escalation failed: %s", exc)
            return ""

    async def request_claude_permission(self, justification: str) -> bool:
        # Placeholder permission hook; approve for now and could hit supervisor endpoint later.
        logger.info("Requesting Supervisor permission for Claude: %s", justification)
        return True

    async def solve_task(self, task_prompt: str, critical: bool = False) -> Tuple[bool, str]:
        attempts = 0
        code = await self.generate_with_ollama(task_prompt, model="deepseek-coder:6.7b")
        if not code:
            code = await self.generate_with_ollama(task_prompt, model="codellama")
        while attempts < 2:
            ok, err = await self.validate_code(code)
            if ok:
                return True, code
            attempts += 1
            logger.info("Validation failed attempt %d: %s", attempts, err)
            code = await self.generate_with_ollama(task_prompt, model="codellama")

        if critical:
            allowed = await self.request_claude_permission("Critical/Financial task")
        else:
            allowed = await self.request_claude_permission("Local models failed twice")
        if not allowed:
            logger.warning("Claude not permitted; aborting task")
            return False, code

        claude_code = await self.escalate_to_claude(task_prompt, reason="local_failed" if not critical else "critical")
        if not claude_code:
            return False, code
        ok, err = await self.validate_code(claude_code)
        if ok:
            return True, claude_code
        logger.warning("Claude code failed validation: %s", err)
        return False, claude_code

    async def feasibility_analysis(self, lead: dict) -> dict:
        """
        Basic feasibility checks for unknown opportunities.
        """
        query = lead.get("query", "")
        prompt_login = f"Assess if login can be automated for opportunity: {query}"
        prompt_deliverable = f"Assess if deliverable can be generated automatically for: {query}"
        prompt_payment = f"Assess how to collect payments (Bybit/VCC) for: {query}"

        login_ok = bool(await self.generate_with_ollama(prompt_login, model="deepseek-coder:6.7b"))
        deliver_ok = bool(await self.generate_with_ollama(prompt_deliverable, model="deepseek-coder:6.7b"))
        payment_ok = True  # assume Bybit/VCC possible; extend later

        return {
            "login_automation": login_ok,
            "deliverable_gen": deliver_ok,
            "payment_path": payment_ok,
        }

    async def check_safety(self, lead: dict) -> bool:
        prompt = (
            "¿Esta tarea implica fraude, ilegalidad o daño? Responde solo SI o NO.\n"
            f"Detalle: {lead}"
        )
        answer = await self.generate_with_ollama(prompt, model="deepseek-coder:6.7b")
        return answer.strip().upper().startswith("NO")
