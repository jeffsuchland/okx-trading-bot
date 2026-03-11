"""Periodic account balance synchronization with OKX."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from src.exchange.okx_client import OkxClient

logger = logging.getLogger(__name__)


class BalanceSync:
    """Periodically polls OKX account API and maintains an in-memory balance snapshot."""

    def __init__(
        self,
        client: OkxClient,
        poll_interval: float = 5.0,
        on_balance_updated: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._client = client
        self._poll_interval = poll_interval
        self._on_balance_updated = on_balance_updated
        self._running = False
        self._task: asyncio.Task[None] | None = None

        # Snapshot state
        self._usdt_balance: float = 0.0
        self._total_equity: float = 0.0
        self._positions: list[dict[str, Any]] = []
        self._last_snapshot: dict[str, Any] = {}

    def get_usdt_balance(self) -> float:
        """Return current available USDT balance."""
        return self._usdt_balance

    def get_total_equity(self) -> float:
        """Return total account equity in USDT terms."""
        return self._total_equity

    def get_positions(self) -> list[dict[str, Any]]:
        """Return list of open positions with size, entry price, unrealized PnL."""
        return list(self._positions)

    async def _poll(self) -> None:
        """Single poll cycle: fetch balance and update snapshot."""
        try:
            balance = self._client.get_account_balance("USDT")
            new_snapshot = {
                "usdt_available": balance.get("available", 0.0),
                "total_equity": balance.get("equity", 0.0),
                "frozen": balance.get("frozen", 0.0),
            }

            self._usdt_balance = new_snapshot["usdt_available"]
            self._total_equity = new_snapshot["total_equity"]

            # Check if snapshot changed
            if new_snapshot != self._last_snapshot:
                self._last_snapshot = new_snapshot
                if self._on_balance_updated:
                    self._on_balance_updated(new_snapshot)

            logger.debug(
                "Balance synced: USDT=%.2f, Equity=%.2f",
                self._usdt_balance,
                self._total_equity,
            )
        except Exception as e:
            logger.error("Balance sync failed: %s", e)

    async def _sync_positions(self) -> None:
        """Fetch open positions from the account API."""
        try:
            # Use the account API to get positions
            response = self._client._account_api.get_positions()
            self._client._check_response(response)
            raw_positions = response.get("data", [])
            self._positions = [
                {
                    "symbol": p.get("instId", ""),
                    "size": float(p.get("pos", 0)),
                    "entry_price": float(p.get("avgPx", 0)),
                    "unrealized_pnl": float(p.get("upl", 0)),
                    "side": "long" if float(p.get("pos", 0)) > 0 else "short",
                }
                for p in raw_positions
                if float(p.get("pos", 0)) != 0
            ]
        except Exception as e:
            logger.error("Position sync failed: %s", e)

    async def _loop(self) -> None:
        """Main polling loop."""
        while self._running:
            await self._poll()
            await self._sync_positions()
            await asyncio.sleep(self._poll_interval)

    def start(self) -> asyncio.Task[None]:
        """Start the balance sync polling loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Balance sync started (interval=%.1fs)", self._poll_interval)
        return self._task

    async def stop(self) -> None:
        """Stop the balance sync polling loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Balance sync stopped")
