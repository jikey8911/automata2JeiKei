"""
Localized Finance Manager for autonomous UAE agents.
Uses the global CCXT executor proxy and specific subaccount UID.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class UaeFinanceManager:
    """
    Manages exchange operations for a single UAE subaccount via CCXT proxy.
    """

    def __init__(self, uid: Optional[str] = None, proxy_url: Optional[str] = None) -> None:
        # 1. Load configuration from environment or constructor
        self.uid = uid or os.getenv("BYBIT_SUB_UID")
        self.proxy_url = proxy_url or os.getenv("CCXT_PROXY_URL") or "http://100.90.90.65:8000"
        
        # 2. Balance Cache (TTL: 40 seconds as requested)
        self._balance_cache: Dict[str, float] = {}
        self._cache_expiry = 0.0
        self._cache_ttl = 40.0
        
        if not self.uid:
            logger.warning("UaeFinanceManager initialized WITHOUT a UID. Some calls may fail.")
        logger.info("UaeFinanceManager ready | UID: %s | Proxy: %s", self.uid, self.proxy_url)

    async def _call_ccxt(self, method: str, args: list | None = None) -> Any:
        """
        Internal helper to route CCXT calls through the remote executor.
        """
        payload = {
            "method": method,
            "args": args or [],
            "uid": self.uid,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = self.proxy_url.rstrip("/") + "/ejecutar"
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                if not data.get("ok"):
                    raise RuntimeError(f"CCXT Remote Error: {data.get('error')}")
                
                return data.get("result")
        except Exception as exc:
            logger.error("CCXT Proxy call failed (%s): %s", method, exc)
            raise

    async def get_balance(self) -> Dict[str, float]:
        """
        Fetch subaccount balances (USDT/USDC). Uses 40s cache.
        """
        now = time.time()
        if self._balance_cache and now < self._cache_expiry:
            return self._balance_cache

        try:
            # We use fetch_balance from CCXT
            res = await self._call_ccxt("fetch_balance")
            
            # Format CCXT standard response to a simple dict
            total = res.get("total", {})
            balances = {
                "USDT": float(total.get("USDT", 0.0)),
                "USDC": float(total.get("USDC", 0.0)),
            }
            
            self._balance_cache = balances
            self._cache_expiry = now + self._cache_ttl
            return balances
        except Exception as exc:
            logger.warning("Failed to fetch balance via CCXT proxy: %s", exc)
            return self._balance_cache or {"USDT": 0.0, "USDC": 0.0}

    async def create_market_buy_order(self, symbol: str, amount: float) -> Dict:
        """
        Execute a market buy order using CCXT.
        """
        return await self._call_ccxt("create_market_buy_order", [symbol, amount])

    async def create_market_sell_order(self, symbol: str, amount: float) -> Dict:
        """
        Execute a market sell order using CCXT.
        """
        return await self._call_ccxt("create_market_sell_order", [symbol, amount])

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> list:
        """
        Retrieve open orders.
        """
        args = [symbol] if symbol else []
        return await self._call_ccxt("fetch_open_orders", args)

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        """
        Cancel an order.
        """
        return await self._call_ccxt("cancel_order", [order_id, symbol])


class UaeVirtualCardManager:
    """
    Skeleton for VCC management within a single UAE context.
    """

    def __init__(self, exchange: UaeFinanceManager) -> None:
        self.exchange = exchange

    async def issue_card(self, limit: float) -> Dict[str, str]:
        """
        Request a new VCC with specific spending limit.
        Returns pseudo card data for current skeletal implementation.
        """
        logger.info("UAE issuing VCC (limit: %.2f) for subaccount: %s", limit, self.exchange.uid)
        
        # In a real scenario, this would call a Stripe/Marqeta/CryptoVCC API
        card_id = f"uae-vcc-{uuid.uuid4().hex[:8]}"
        number = f"4532{uuid.uuid4().hex[:12]}" # Pseudo numbers
        cvv = uuid.uuid4().hex[:3]
        exp = "12/28"
        
        return {
            "card_id": card_id,
            "number": number,
            "cvv": cvv,
            "exp": exp,
            "limit": limit
        }

    async def fund_card(self, amount: float) -> Dict:
        """
        Fund card from subaccount balance.
        """
        # Ensure we have balance
        bal = await self.exchange.get_balance()
        if bal.get("USDT", 0) < amount:
            raise RuntimeError(f"Insufficient funds in UAE subaccount to fund VCC. Required: {amount}")
        
        logger.info("UAE funding VCC with %.2f USDT", amount)
        # In a real integration, this might trigger a transfer or top-up via API
        return {"status": "funded", "amount": amount}

    async def top_up_card(self, card_id: str, amount: float) -> Dict:
        """
        Top up an existing VCC.
        """
        return await self.fund_card(amount)
