"""
Exchange finance operations via CCXT (spot/funding friendly).
Transfers/subaccounts are no-ops for exchanges que no soportan
movimientos internos; se mantienen para compatibilidad con el Supervisor.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import uuid
import secrets
from typing import Dict, Optional

import ccxt
import httpx

from .database import EncryptedSecretStore, DEFAULT_DB_PATH
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ExchangeManager:
    def __init__(
        self,
        secret_store: Optional[EncryptedSecretStore] = None,
        testnet: bool = False,
        master_uid: Optional[str] = None,
    ) -> None:
        self.store = secret_store or EncryptedSecretStore()
        self.exchange_name = (self.store.get_secret("EXCHANGE_NAME") or os.getenv("EXCHANGE_NAME") or "bybit").lower()
        self.ccxt_proxy = self.store.get_secret("CCXT_PROXY_URL") or os.getenv("CCXT_PROXY_URL") or "http://100.90.90.65:8000"
        # Buscar claves específicas del exchange, si no, caer en BYBIT_*
        upper = self.exchange_name.replace(" ", "").replace("-", "").upper()
        self.api_key = (
            self.store.get_secret(f"{upper}_API_KEY")
            or self.store.get_secret("BYBIT_API_KEY")
            or os.getenv(f"{upper}_API_KEY")
            or os.getenv("BYBIT_API_KEY", "")
        )
        self.api_secret = (
            self.store.get_secret(f"{upper}_API_SECRET")
            or self.store.get_secret("BYBIT_API_SECRET")
            or os.getenv(f"{upper}_API_SECRET")
            or os.getenv("BYBIT_API_SECRET", "")
        )
        self.master_uid = master_uid or self.store.get_secret("BYBIT_MASTER_UID") or os.getenv("BYBIT_MASTER_UID")

        try:
            if not hasattr(ccxt, self.exchange_name):
                raise ValueError(f"Exchange '{self.exchange_name}' no soportado por ccxt")
            
            class OrdenCCXT(BaseModel):
                exchange_name: str    # ej: 'binance', 'kraken'
                api_key: str
                secret: str
                uid: str | None = None  # Bybit subaccount UUID (optional)
                method: str           # ej: 'fetch_ticker', 'fetch_balance'
                args: list = []       # Argumentos normales (ej: ['BTC/USDT'])
                kwargs: dict = {}     # Argumentos extra (ej: {'amount': 1})

            cls = getattr(ccxt, self.exchange_name)
            exchange_kwargs = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
            }
            if self.master_uid:
                exchange_kwargs["uid"] = self.master_uid
            self.client = cls(exchange_kwargs)
        except Exception as exc:
            logger.exception("Failed to init ccxt client for %s: %s", self.exchange_name, exc)
            raise
        self._init_audit_db()

    async def _remote_call(self, method: str, args: list | None = None, kwargs: dict | None = None) -> Dict:
        """
        Si CCXT_PROXY_URL está definido, manda la llamada a un ejecutor remoto (por ej. PC con Tailscale).
        """
        if not self.ccxt_proxy:
            raise RuntimeError("CCXT proxy no configurado")
        payload = {
            "exchange_name": self.exchange_name,
            "api_key": self.api_key,
            "secret": self.api_secret,
            "uid": self.master_uid,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(self.ccxt_proxy.rstrip("/") + "/ejecutar", json=payload)
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "exito":
                raise RuntimeError(f"Proxy error: {data}")
            return data.get("data", {})

    def _init_audit_db(self) -> None:
        try:
            conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transfer_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    direction TEXT NOT NULL,
                    uae_id TEXT,
                    amount REAL NOT NULL,
                    transfer_id TEXT NOT NULL,
                    raw_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.exception("Failed to init transfer_audit table: %s", exc)
            raise

    async def _call(self, func, **kwargs):
        return await asyncio.to_thread(func, **kwargs)

    async def _call_ccxt(self, method_name: str, *args, **kwargs) -> Dict:
        """Execute a CCXT method either locally or via remote proxy.
        If CCXT_PROXY_URL is configured, the call is forwarded to the remote executor.
        Otherwise, it uses the local ccxt client.
        """
        if self.ccxt_proxy:
            # Remote execution expects args as a list and kwargs as a dict
            return await self._remote_call(method_name, list(args), kwargs)
        else:
            method = getattr(self.client, method_name)
            return await self._call(method, *args, **kwargs)

    async def _log_transfer(self, direction: str, uae_id: str, amount: float, transfer_id: str, response: Dict) -> None:
        try:
            conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
            conn.execute(
                "INSERT INTO transfer_audit (direction, uae_id, amount, transfer_id, raw_response) VALUES (?, ?, ?, ?, ?);",
                (direction, uae_id, amount, transfer_id, str(response)),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.exception("Failed to audit transfer %s: %s", transfer_id, exc)

    async def get_genesis_balance(self) -> Dict[str, float]:
        """
        Spot/funding balances (USDT/USDC) usando fetch_balance.
        """
        try:
            bal = await self._call_ccxt("fetch_balance")
            total = bal.get("total", {}) if isinstance(bal, dict) else {}
            return {
                "USDT": float(total.get("USDT", 0.0) or 0.0),
                "USDC": float(total.get("USDC", 0.0) or 0.0),
            }
        except Exception as exc:
            logger.warning("%s balance failed: %s", self.exchange_name, exc)
            return {"USDT": 0.0, "USDC": 0.0}

    async def get_trading_balance(self, coin: str = "USDT") -> float:
        try:
            bal = await self._call_ccxt("fetch_balance")
            return float(bal.get("total", {}).get(coin, 0.0) or 0.0)
        except Exception as exc:
            logger.warning("%s trading balance failed: %s", self.exchange_name, exc)
            return 0.0

    async def create_subaccount(self, name: str) -> Optional[str]:
        """
        Intentar crear subcuenta en Bybit usando v5 create_sub_account.
        """
        try:
            if self.exchange_name == "bybit":
                # Bybit expects subMemberName (max 30 chars), memberType=1 (Normal)
                res = await self._call_ccxt("create_sub_account", memberType=1, subMemberName=name[:30])
                sub_uid = res.get("subMemberId")
                if sub_uid:
                    logger.info("Successfully created Bybit subaccount: %s for UAE %s", sub_uid, name)
                    return str(sub_uid)
            
            # Fallback
            fallback = self.master_uid or os.getenv("BYBIT_FALLBACK_SUB_UID")
            if fallback:
                logger.info("Using fallback sub UID=%s", fallback)
                return fallback
            return None
        except Exception as exc:
            logger.warning("create_subaccount failed on %s: %s", self.exchange_name, exc)
            return None

    async def distribute_to_uae(self, uae_id: str, sub_uid: str, amount: float, coin: str = "USDT") -> Dict:
        """
        Realiza una transferencia interna desde la cuenta Maestra a la Subcuenta.
        """
        transfer_id = str(uuid.uuid4())
        try:
            # Bybit Inter-account transfer (SPOT to SPOT)
            # Para Bybit v5, se usa transfer(coin, amount, fromAccount, toAccount, params={'toMemberId': sub_uid})
            res = await self._call_ccxt(
                "transfer", 
                coin, 
                amount, 
                "SPOT", 
                "SPOT", 
                params={"toMemberId": sub_uid}
            )
            await self._log_transfer("to_uae_success", uae_id, amount, transfer_id, res)
            logger.info("Transferencia exitosa a UAE %s (%s): %.2f %s", uae_id, sub_uid, amount, coin)
            return res
        except Exception as exc:
            logger.error("distribute_to_uae failed: %s", exc)
            await self._log_transfer("to_uae_failed", uae_id, amount, transfer_id, {"error": str(exc)})
            return {"error": str(exc)}

    async def collect_taxes(self, uae_id: str, amount: float, coin: str = "USDT") -> Dict:
        """
        No-op en ccxt genérico. Solo auditamos el intento.
        """
        transfer_id = str(uuid.uuid4())
        logger.warning("collect_taxes no implementado para %s; amount=%.2f", self.exchange_name, amount)
        await self._log_transfer("tax_failed", uae_id, amount, transfer_id, {"error": "not_implemented"})
        return {}

    async def rebalance_to_funding(self, cushion: float = 50.0, coin: str = "USDT") -> Optional[Dict]:
        """
        No-op en ccxt genérico (cada exchange difiere). Auditamos el exceso detectado.
        """
        balance = await self.get_trading_balance(coin=coin)
        if balance <= cushion:
            return None
        excess = balance - cushion
        transfer_id = str(uuid.uuid4())
        logger.warning("rebalance_to_funding no implementado para %s; exceso=%.2f", self.exchange_name, excess)
        await self._log_transfer("rebalance_skipped", "GENESIS", excess, transfer_id, {"warning": "not_implemented"})
        return None


class VirtualCardManager:
    """
    Skeleton for VCC purchases funded from exchange profits.
    """

    def __init__(self, exchange: ExchangeManager) -> None:
        self.exchange = exchange

    async def fund_card(self, amount: float, coin: str = "USDT") -> None:
        # Placeholder: integrate with issuer; currently ensure funds in FUND wallet
        await self.exchange.rebalance_to_funding(cushion=amount, coin=coin)

    async def purchase(self, description: str, amount: float) -> None:
        logger.info("VCC purchase requested: %s amount=%.2f (not yet implemented)", description, amount)

    async def issue_card(self, sub_uid: str, limit: float) -> Dict[str, str]:
        """
        Placeholder for one-time VCC issuance. Returns pseudo card data until issuer integration is added.
        """
        logger.info("Issuing one-time VCC for sub_uid=%s (limit=%.2f)", sub_uid, limit)
        # Generate pseudo secure tokens to avoid plaintext logging
        number = uuid.uuid4().hex[:16]
        cvv = uuid.uuid4().hex[:3]
        exp = "12/29"
        card_id = f"vcc-{uuid.uuid4().hex[:8]}"
        return {"card_id": card_id, "number": number, "cvv": cvv, "exp": exp}

    async def top_up_card(self, card_id: str, amount_usd: float, coin: str = "USDT") -> Dict:
        """
        Top-up VCC by moving funds from trading to funding, then invoking VCC API (skeleton).
        """
        await self.exchange.rebalance_to_funding(cushion=amount_usd, coin=coin)
        logger.info("Top-up VCC %s with %.2f USD equivalent", card_id, amount_usd)
        # Placeholder for real VCC API call
        return {"card_id": card_id, "amount": amount_usd, "status": "queued"}


__all__ = ["ExchangeManager", "VirtualCardManager"]
