"""Stop-loss automation for open positions."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StopLossManager:
    """Manages stop-loss levels for open positions.

    Supports fixed percentage and trailing stop modes.
    """

    def __init__(
        self,
        default_pct: float = 2.0,
        mode: str = "fixed",
    ) -> None:
        self._default_pct = default_pct
        self._mode = mode  # "fixed" or "trailing"
        # symbol -> {"stop_price": float, "entry_price": float, "highest_price": float}
        self._stop_levels: dict[str, dict[str, float]] = {}
        self._closing: set[str] = set()

    def _calculate_stop_price(self, entry_price: float) -> float:
        """Calculate the stop price based on entry and default percentage."""
        return entry_price * (1 - self._default_pct / 100.0)

    def check_positions(self, positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Evaluate each position against its stop-loss level.

        Args:
            positions: List of position dicts with keys: symbol, entry_price, current_price, size, side.

        Returns:
            List of positions that should be closed (stop triggered).
        """
        triggered: list[dict[str, Any]] = []

        for pos in positions:
            symbol = pos.get("symbol", "")
            entry_price = float(pos.get("entry_price", 0))
            current_price = float(pos.get("current_price", 0))
            side = pos.get("side", "long")

            if symbol in self._closing:
                continue

            if entry_price <= 0 or current_price <= 0:
                continue

            # Initialize stop level if not tracked
            if symbol not in self._stop_levels:
                self._stop_levels[symbol] = {
                    "stop_price": self._calculate_stop_price(entry_price),
                    "entry_price": entry_price,
                    "highest_price": current_price,
                }

            level = self._stop_levels[symbol]

            # Trailing stop: update stop price upward as profit increases
            if self._mode == "trailing":
                if current_price > level["highest_price"]:
                    level["highest_price"] = current_price
                    level["stop_price"] = current_price * (1 - self._default_pct / 100.0)

            # Check if stop is triggered (for long positions)
            if side == "long" and current_price <= level["stop_price"]:
                logger.warning(
                    "Stop-loss triggered for %s: current=%.2f <= stop=%.2f",
                    symbol, current_price, level["stop_price"],
                )
                triggered.append(pos)
                self._closing.add(symbol)

        return triggered

    def get_stop_levels(self) -> dict[str, dict[str, float]]:
        """Return current stop prices for all tracked positions."""
        return dict(self._stop_levels)

    def mark_closed(self, symbol: str) -> None:
        """Remove a position from tracking after it has been closed."""
        self._stop_levels.pop(symbol, None)
        self._closing.discard(symbol)

    def update_config(self, default_pct: float | None = None, mode: str | None = None) -> None:
        """Hot-reload stop-loss parameters."""
        if default_pct is not None:
            self._default_pct = default_pct
        if mode is not None:
            self._mode = mode
        logger.info("StopLoss config updated: pct=%.2f, mode=%s", self._default_pct, self._mode)
