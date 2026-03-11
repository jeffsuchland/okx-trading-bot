"""Position sizing engine for trade quantity calculation."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates order quantity based on spend-per-trade and max exposure limits."""

    def __init__(
        self,
        spend_per_trade: float = 10.0,
        max_total_exposure: float = 100.0,
    ) -> None:
        self._spend_per_trade = spend_per_trade
        self._max_total_exposure = max_total_exposure
        self._current_exposure: float = 0.0

    def calculate_qty(self, price: float, current_exposure: float | None = None) -> float:
        """Calculate the quantity to buy given spend_per_trade and current price.

        Args:
            price: Current asset price.
            current_exposure: Override for current exposure tracking. If None, uses internal state.

        Returns:
            Quantity to buy. Returns 0 if the trade would exceed max_total_exposure.
        """
        if price <= 0:
            return 0.0

        exposure = current_exposure if current_exposure is not None else self._current_exposure

        if exposure + self._spend_per_trade > self._max_total_exposure:
            logger.warning(
                "Trade blocked: exposure %.2f + spend %.2f > max %.2f",
                exposure,
                self._spend_per_trade,
                self._max_total_exposure,
            )
            return 0.0

        qty = self._spend_per_trade / price
        return round(qty, 8)

    def update_exposure(self, trade_info: dict[str, Any]) -> None:
        """Adjust tracked current exposure after a fill.

        Args:
            trade_info: Dict with keys: side, qty, price.
                        'buy' increases exposure, 'sell' decreases it.
        """
        side = trade_info.get("side", "")
        qty = float(trade_info.get("qty", 0))
        price = float(trade_info.get("price", 0))
        value = qty * price

        if side == "buy":
            self._current_exposure += value
        elif side == "sell":
            self._current_exposure = max(0.0, self._current_exposure - value)

        logger.debug("Exposure updated: %.2f (after %s)", self._current_exposure, side)

    def get_current_exposure(self) -> float:
        """Return the total USDT value currently at risk."""
        return self._current_exposure

    def update_config(
        self,
        spend_per_trade: float | None = None,
        max_total_exposure: float | None = None,
    ) -> None:
        """Hot-reload position sizing parameters."""
        if spend_per_trade is not None:
            self._spend_per_trade = spend_per_trade
        if max_total_exposure is not None:
            self._max_total_exposure = max_total_exposure
        logger.info(
            "PositionSizer config updated: spend=%.2f, max_exposure=%.2f",
            self._spend_per_trade,
            self._max_total_exposure,
        )
