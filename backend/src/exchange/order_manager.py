"""High-level order lifecycle management service."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from src.exchange.okx_client import OkxClient

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order placement, cancellation, tracking, and panic flatten."""

    def __init__(
        self,
        client: OkxClient,
        max_requests_per_window: int = 60,
        window_seconds: float = 2.0,
    ) -> None:
        self._client = client
        self._open_orders: dict[str, dict[str, Any]] = {}
        self._max_requests = max_requests_per_window
        self._window_seconds = window_seconds
        self._request_timestamps: list[float] = []

    def _throttle(self) -> None:
        """Block if we've exceeded the rate limit window."""
        now = time.monotonic()
        # Remove timestamps outside the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if now - ts < self._window_seconds
        ]
        if len(self._request_timestamps) >= self._max_requests:
            sleep_time = self._window_seconds - (now - self._request_timestamps[0])
            if sleep_time > 0:
                logger.warning("Rate limit reached, sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
        self._request_timestamps.append(time.monotonic())

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        price: str,
        trade_mode: str = "cash",
    ) -> dict[str, Any]:
        """Place a limit order and track it internally."""
        self._throttle()
        result = self._client.place_order(
            symbol=symbol,
            side=side,
            size=qty,
            price=price,
            order_type="limit",
            trade_mode=trade_mode,
        )
        order_id = result["order_id"]
        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "open",
        }
        self._open_orders[order_id] = order_record
        logger.info("Placed limit order %s: %s %s %s @ %s", order_id, side, qty, symbol, price)
        return result

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        trade_mode: str = "cash",
    ) -> dict[str, Any]:
        """Place a market order (used for panic flatten)."""
        self._throttle()
        result = self._client.place_order(
            symbol=symbol,
            side=side,
            size=qty,
            order_type="market",
            trade_mode=trade_mode,
        )
        logger.info("Placed market order: %s %s %s", side, qty, symbol)
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Cancel a specific order and remove from tracking."""
        self._throttle()
        result = self._client.cancel_order(symbol=symbol, order_id=order_id)
        self._open_orders.pop(order_id, None)
        logger.info("Cancelled order %s on %s", order_id, symbol)
        return result

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Return list of currently tracked open orders."""
        return list(self._open_orders.values())

    async def cancel_all_orders(self) -> list[dict[str, Any]]:
        """Cancel all tracked open orders."""
        results = []
        for order_id, order in list(self._open_orders.items()):
            try:
                result = await self.cancel_order(order["symbol"], order_id)
                results.append(result)
            except Exception as e:
                logger.error("Failed to cancel order %s: %s", order_id, e)
        self._open_orders.clear()
        logger.info("Cancelled all open orders (%d)", len(results))
        return results

    async def panic_flatten(self, positions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Cancel all orders and market-sell all non-USDT positions.

        Args:
            positions: List of position dicts with keys: symbol, size, side.
                       If None, only cancels orders.
        """
        cancel_results = await self.cancel_all_orders()

        sell_results = []
        if positions:
            for pos in positions:
                symbol = pos.get("symbol", "")
                size = pos.get("size", "0")
                # Determine the closing side (opposite of current position)
                pos_side = pos.get("side", "long")
                close_side = "sell" if pos_side == "long" else "buy"
                try:
                    result = await self.place_market_order(
                        symbol=symbol,
                        side=close_side,
                        qty=size,
                    )
                    sell_results.append(result)
                except Exception as e:
                    logger.error("Failed to flatten position %s: %s", symbol, e)

        logger.info(
            "Panic flatten complete: %d orders cancelled, %d positions closed",
            len(cancel_results),
            len(sell_results),
        )
        return {
            "orders_cancelled": len(cancel_results),
            "positions_closed": len(sell_results),
            "cancel_results": cancel_results,
            "sell_results": sell_results,
        }
