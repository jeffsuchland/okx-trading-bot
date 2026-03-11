"""Grid trading strategy."""

from __future__ import annotations

import logging
from typing import Any

from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "num_levels": 5,
    "spacing_pct": 0.5,
    "order_size_usdt": 10.0,
}


class GridTradingStrategy(BaseStrategy):
    """Grid strategy that places buy/sell limit orders at fixed intervals around the current price.

    Rebalances the grid when the price moves beyond the outermost level.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        merged = {**DEFAULT_CONFIG, **(config or {})}
        super().__init__(config=merged)
        self._current_price: float | None = None
        self._grid_center: float | None = None
        self._active_levels: set[float] = set()

    def analyze(self, market_data: dict[str, Any]) -> None:
        """Update current price from market data."""
        if "last" in market_data:
            self._current_price = float(market_data["last"])
        elif "close" in market_data:
            self._current_price = float(market_data["close"])
        elif "data" in market_data:
            for item in market_data["data"]:
                if "last" in item:
                    self._current_price = float(item["last"])
                elif "c" in item:
                    self._current_price = float(item["c"])

    @staticmethod
    def calculate_grid_levels(
        current_price: float,
        num_levels: int,
        spacing_pct: float,
    ) -> tuple[list[float], list[float]]:
        """Calculate buy and sell grid price levels around the current price.

        Args:
            current_price: The center price for the grid.
            num_levels: Number of levels on each side.
            spacing_pct: Percentage spacing between levels.

        Returns:
            Tuple of (buy_levels, sell_levels) sorted closest-to-price first.
        """
        spacing_mult = spacing_pct / 100.0
        buy_levels: list[float] = []
        sell_levels: list[float] = []

        for i in range(1, num_levels + 1):
            buy_price = round(current_price * (1 - spacing_mult * i), 8)
            sell_price = round(current_price * (1 + spacing_mult * i), 8)
            buy_levels.append(buy_price)
            sell_levels.append(sell_price)

        return buy_levels, sell_levels

    def _needs_rebalance(self) -> bool:
        """Check if the price has moved beyond the outermost grid level."""
        if self._current_price is None or self._grid_center is None:
            return True
        if not self._active_levels:
            return True

        num_levels = int(self.config["num_levels"])
        spacing_pct = float(self.config["spacing_pct"])
        spacing_mult = spacing_pct / 100.0
        outer_distance = spacing_mult * num_levels

        lower_bound = self._grid_center * (1 - outer_distance)
        upper_bound = self._grid_center * (1 + outer_distance)

        return self._current_price < lower_bound or self._current_price > upper_bound

    def generate_signal(self) -> dict[str, Any]:
        """Generate grid orders to place, avoiding duplicate price levels."""
        if self._current_price is None:
            return {"action": "HOLD", "reason": "no price data", "orders": []}

        num_levels = int(self.config["num_levels"])
        spacing_pct = float(self.config["spacing_pct"])
        order_size_usdt = float(self.config["order_size_usdt"])

        if self._needs_rebalance():
            self._grid_center = self._current_price
            self._active_levels.clear()
            logger.info("Grid rebalanced around %.2f", self._current_price)

        buy_levels, sell_levels = self.calculate_grid_levels(
            self._grid_center,  # type: ignore[arg-type]
            num_levels,
            spacing_pct,
        )

        orders: list[dict[str, Any]] = []

        for price in buy_levels:
            if price not in self._active_levels:
                qty = round(order_size_usdt / price, 8) if price > 0 else 0
                orders.append({
                    "side": "buy",
                    "price": price,
                    "qty": qty,
                })
                self._active_levels.add(price)

        for price in sell_levels:
            if price not in self._active_levels:
                qty = round(order_size_usdt / price, 8) if price > 0 else 0
                orders.append({
                    "side": "sell",
                    "price": price,
                    "qty": qty,
                })
                self._active_levels.add(price)

        if orders:
            return {
                "action": "GRID",
                "orders": orders,
                "grid_center": self._grid_center,
                "reason": f"{len(orders)} new grid orders",
            }
        return {
            "action": "HOLD",
            "orders": [],
            "grid_center": self._grid_center,
            "reason": "all grid levels already active",
        }

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        """Log signal; actual order execution is delegated to the trading loop."""
        if signal.get("action") == "HOLD":
            return None
        logger.info("Grid signal: %s", signal.get("reason", ""))
        return signal
