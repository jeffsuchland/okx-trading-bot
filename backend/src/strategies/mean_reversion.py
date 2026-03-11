"""RSI/MACD mean-reversion trading strategy."""

from __future__ import annotations

import logging
from typing import Any

from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
}


class MeanReversionStrategy(BaseStrategy):
    """Mean-reversion strategy using RSI and MACD indicators.

    Generates BUY when RSI < oversold AND MACD histogram crosses above zero.
    Generates SELL when RSI > overbought AND MACD histogram crosses below zero.
    Otherwise HOLD.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        merged = {**DEFAULT_CONFIG, **(config or {})}
        super().__init__(config=merged)
        self._prices: list[float] = []
        self._last_histogram: float | None = None

    def analyze(self, market_data: dict[str, Any]) -> None:
        """Consume candle close prices from market data."""
        if "close" in market_data:
            self._prices.append(float(market_data["close"]))
        elif "data" in market_data:
            for candle in market_data["data"]:
                if "c" in candle:
                    self._prices.append(float(candle["c"]))

    def generate_signal(self) -> dict[str, Any]:
        """Generate BUY/SELL/HOLD signal based on RSI and MACD."""
        rsi_period = int(self.config["rsi_period"])
        macd_fast = int(self.config["macd_fast"])
        macd_slow = int(self.config["macd_slow"])
        macd_signal_period = int(self.config["macd_signal"])

        min_required = macd_slow + macd_signal_period + 1
        if len(self._prices) < min_required:
            return {"action": "HOLD", "reason": "insufficient data"}

        rsi = self.calculate_rsi(self._prices, rsi_period)
        _, _, histogram = self.calculate_macd(
            self._prices, macd_fast, macd_slow, macd_signal_period
        )

        current_rsi = rsi[-1]
        current_hist = histogram[-1]
        prev_hist = histogram[-2] if len(histogram) >= 2 else 0.0

        # Detect MACD histogram zero-line crossover
        hist_crossed_up = prev_hist <= 0 and current_hist > 0
        hist_crossed_down = prev_hist >= 0 and current_hist < 0

        oversold = float(self.config["rsi_oversold"])
        overbought = float(self.config["rsi_overbought"])

        self._last_histogram = current_hist

        if current_rsi < oversold and hist_crossed_up:
            return {
                "action": "BUY",
                "rsi": current_rsi,
                "macd_histogram": current_hist,
                "reason": f"RSI={current_rsi:.1f} < {oversold} and MACD histogram crossed up",
            }
        elif current_rsi > overbought and hist_crossed_down:
            return {
                "action": "SELL",
                "rsi": current_rsi,
                "macd_histogram": current_hist,
                "reason": f"RSI={current_rsi:.1f} > {overbought} and MACD histogram crossed down",
            }
        else:
            return {
                "action": "HOLD",
                "rsi": current_rsi,
                "macd_histogram": current_hist,
                "reason": "conditions not met",
            }

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        """Log signal; actual order execution is delegated to the trading loop."""
        action = signal.get("action", "HOLD")
        if action == "HOLD":
            return None
        logger.info("Mean reversion signal: %s — %s", action, signal.get("reason", ""))
        return signal

    @staticmethod
    def calculate_rsi(prices: list[float], period: int = 14) -> list[float]:
        """Calculate RSI using Wilder's smoothing method.

        Args:
            prices: List of closing prices.
            period: RSI lookback period (default 14).

        Returns:
            List of RSI values (same length as prices, first `period` values are 0).
        """
        if len(prices) < period + 1:
            return [50.0] * len(prices)

        rsi_values: list[float] = [0.0] * period

        # Calculate initial average gain/loss
        gains: list[float] = []
        losses: list[float] = []
        for i in range(1, period + 1):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

        # Wilder's smoothing for subsequent values
        for i in range(period + 1, len(prices)):
            change = prices[i] - prices[i - 1]
            gain = max(change, 0)
            loss = max(-change, 0)

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

        return rsi_values

    @staticmethod
    def calculate_macd(
        prices: list[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> tuple[list[float], list[float], list[float]]:
        """Calculate MACD line, signal line, and histogram.

        Args:
            prices: List of closing prices.
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26).
            signal_period: Signal line EMA period (default 9).

        Returns:
            Tuple of (macd_line, signal_line, histogram) lists.
        """

        def ema(data: list[float], period: int) -> list[float]:
            """Calculate Exponential Moving Average."""
            if not data:
                return []
            multiplier = 2.0 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                val = (data[i] - result[-1]) * multiplier + result[-1]
                result.append(val)
            return result

        fast_ema = ema(prices, fast_period)
        slow_ema = ema(prices, slow_period)

        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = ema(macd_line, signal_period)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]

        return macd_line, signal_line, histogram
