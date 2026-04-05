"""
Bybit finance operations (async wrappers around pybit unified_trading).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import uuid
import secrets
from typing import Dict, Optional

from pybit.unified_trading import HTTP

from .database import EncryptedSecretStore, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BybitManager:
    def __init__(
        self,
        secret_store: Optional[EncryptedSecretStore] = None,
        testnet: bool = False,
        master_uid: Optional[str] = None,
    ) -> None:
        self.store = secret_store or EncryptedSecretStore()
        self.api_key = self.store.get_secret("BYBIT_API_KEY") or os.getenv("BYBIT_API_KEY", "")
        self.api_secret = self.store.get_secret("BYBIT_API_SECRET") or os.getenv("BYBIT_API_SECRET", "")
        self.master_uid = master_uid or self.store.get_secret("BYBIT_MASTER_UID") or os.getenv("BYBIT_MASTER_UID")
        self.session = HTTP(
            testnet=testnet or not (self.api_key and self.api_secret),
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        self._init_audit_db()

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
        Funding account balances (USDT/USDC) where the card operates.
        """
        try:
            res = await self._call(self.session.get_coins_balance, accountType="FUND")
            coins = res.get("result", {}).get("balance", []) or res.get("result", {}).get("list", [])
            balances = {"USDT": 0.0, "USDC": 0.0}
            for coin in coins:
                name = coin.get("coin") or coin.get("asset")
                if name in balances:
                    balances[name] = float(coin.get("walletBalance") or coin.get("equity") or 0)
            return balances
        except Exception as exc:
            logger.warning("Bybit funding balance failed: %s", exc)
            return {"USDT": 0.0, "USDC": 0.0}

    async def get_trading_balance(self, coin: str = "USDT") -> float:
        try:
            res = await self._call(self.session.get_wallet_balance, accountType="UNIFIED", coin=coin)
            coin_list = res.get("result", {}).get("list", [])
            if not coin_list:
                return 0.0
            coins = coin_list[0].get("coin", [])
            for c in coins:
                if c.get("coin") == coin:
                    return float(c.get("walletBalance", 0))
            return 0.0
        except Exception as exc:
            logger.warning("Bybit trading balance failed: %s", exc)
            return 0.0

    async def create_subaccount(self) -> Optional[str]:
        """
        Create a new sub UID for a UAE. Falls back to master/fallback UID if creation not permitted.
        Uses Bybit V5 create_sub_member with required credentials; if method unavailable, uses raw POST.
        """
        username = f"uae{uuid.uuid4().hex[:8]}"
        # Password rule: 8-30 chars, upper, lower, number
        password = f"Uae{secrets.token_hex(6)}1!"
        try:
            if hasattr(self.session, "create_sub_member"):
                res = await asyncio.to_thread(
                    self.session.create_sub_member,
                    username=username,
                    password=password,
                    memberType=1,  # Normal Sub Account
                )
            else:
                # raw fallback
                res = await asyncio.to_thread(
                    self.session.client._submit_request,  # type: ignore
                    method="POST",
                    path="/v5/user/create-sub-member",
                    query=None,
                    body={
                        "username": username,
                        "password": password,
                        "memberType": 1,
                    },
                    auth=True,
                )
            sub_uid = res.get("result", {}).get("uid")
            if sub_uid:
                logger.info("Created Bybit subaccount UID=%s", sub_uid)
                return sub_uid
        except Exception as exc:
            logger.warning("Failed to create Bybit subaccount: %s", exc)

        fallback = os.getenv("BYBIT_FALLBACK_SUB_UID") or self.master_uid
        if fallback:
            logger.info("Using fallback sub UID=%s", fallback)
            return fallback
        return None

    async def distribute_to_uae(self, uae_id: Optional[str], amount: float, coin: str = "USDT") -> Dict:
        """
        Transfer from Genesis (master UID) FUND -> UAE (sub UID) UNIFIED.
        If target is master_uid (fallback), use internal transfer instead of universal.
        """
        target_uid = uae_id or self.store.get_secret("BYBIT_SUB_ACCOUNT_ID") or self.master_uid
        transfer_id = str(uuid.uuid4())
        try:
            if target_uid == self.master_uid:
                res = await self._call(
                    self.session.create_internal_transfer,
                    transferId=transfer_id,
                    coin=coin,
                    amount=str(amount),
                    fromAccountType="FUND",
                    toAccountType="UNIFIED",
                )
            else:
                res = await self._call(
                    self.session.create_universal_transfer,
                    transferId=transfer_id,
                    coin=coin,
                    amount=str(amount),
                    fromMemberId=self.master_uid,
                    toMemberId=target_uid,
                    fromAccountType="FUND",
                    toAccountType="UNIFIED",
                )
            await self._log_transfer("to_uae", target_uid or "UNKNOWN", amount, transfer_id, res)
            return res
        except Exception as exc:
            logger.exception("Transfer to UAE %s failed: %s", target_uid, exc)
            await self._log_transfer("to_uae_failed", target_uid or "UNKNOWN", amount, transfer_id, {"error": str(exc)})
            return {}

    async def collect_taxes(self, uae_id: str, amount: float, coin: str = "USDT") -> Dict:
        """
        Move funds from UAE sub UID back to Genesis FUND.
        """
        transfer_id = str(uuid.uuid4())
        try:
            res = await self._call(
                self.session.create_universal_transfer,
                transferId=transfer_id,
                coin=coin,
                amount=str(amount),
                fromMemberId=uae_id,
                toMemberId=self.master_uid,
                fromAccountType="UNIFIED",
                toAccountType="FUND",
            )
            await self._log_transfer("tax_from_uae", uae_id, amount, transfer_id, res)
            return res
        except Exception as exc:
            logger.exception("Collect taxes from UAE %s failed: %s", uae_id, exc)
            await self._log_transfer("tax_failed", uae_id, amount, transfer_id, {"error": str(exc)})
            return {}

    async def rebalance_to_funding(self, cushion: float = 50.0, coin: str = "USDT") -> Optional[Dict]:
        """
        Ensure UNIFIED account retains cushion; move excess to FUND.
        """
        balance = await self.get_trading_balance(coin=coin)
        if balance <= cushion:
            return None
        excess = balance - cushion
        transfer_id = str(uuid.uuid4())
        try:
            res = await self._call(
                self.session.create_internal_transfer,
                transferId=transfer_id,
                coin=coin,
                amount=str(excess),
                fromAccountType="UNIFIED",
                toAccountType="FUND",
            )
            await self._log_transfer("rebalance_to_fund", "GENESIS", excess, transfer_id, res)
            logger.info("Moved %.2f %s from trading to funding (cushion %.2f kept)", excess, coin, cushion)
            return res
        except Exception as exc:
            logger.warning("Failed to rebalance liquidity: %s", exc)
            await self._log_transfer("rebalance_failed", "GENESIS", excess, transfer_id, {"error": str(exc)})
            return None


class VirtualCardManager:
    """
    Skeleton for VCC purchases funded from Bybit profits.
    """

    def __init__(self, bybit: BybitManager) -> None:
        self.bybit = bybit

    async def fund_card(self, amount: float, coin: str = "USDT") -> None:
        # Placeholder: integrate with issuer; currently ensure funds in FUND wallet
        await self.bybit.rebalance_to_funding(cushion=amount, coin=coin)

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
        await self.bybit.rebalance_to_funding(cushion=amount_usd, coin=coin)
        logger.info("Top-up VCC %s with %.2f USD equivalent", card_id, amount_usd)
        # Placeholder for real VCC API call
        return {"card_id": card_id, "amount": amount_usd, "status": "queued"}


class OkxManager:
    """
    Placeholder OKX manager to allow failover when Bybit is not reachable.
    """

    def __init__(self, secret_store: Optional[EncryptedSecretStore] = None) -> None:
        self.store = secret_store or EncryptedSecretStore()

    async def get_genesis_balance(self) -> Dict[str, float]:
        logger.warning("OKX manager not implemented; returning zero balances")
        return {"USDT": 0.0, "USDC": 0.0}

    async def distribute_to_uae(self, uae_id: Optional[str], amount: float, coin: str = "USDT") -> Dict:
        logger.warning("OKX distribute_to_uae not implemented; skipping")
        return {}

    async def collect_taxes(self, uae_id: str, amount: float, coin: str = "USDT") -> Dict:
        logger.warning("OKX collect_taxes not implemented; skipping")
        return {}

    async def rebalance_to_funding(self, cushion: float = 50.0, coin: str = "USDT") -> Optional[Dict]:
        logger.warning("OKX rebalance_to_funding not implemented; skipping")
        return None


__all__ = ["BybitManager", "VirtualCardManager", "OkxManager"]
