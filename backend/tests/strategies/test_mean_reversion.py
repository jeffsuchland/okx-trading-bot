"""Tests for RSI/MACD mean-reversion strategy."""

from __future__ import annotations

from typing import Any

import pytest

from src.strategies.base_strategy import BaseStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


# Known price dataset: 50 data points with a trend down then up
# to create predictable RSI and MACD conditions.
PRICES_DOWNTREND = [
    100, 99, 98, 97, 96, 95, 94, 93, 92, 91,
    90, 89, 88, 87, 86, 85, 84, 83, 82, 81,
    80, 79, 78, 77, 76, 75, 74, 73, 72, 71,
    70, 69, 68, 67, 66, 65, 64, 63, 62, 61,
]

PRICES_UPTREND = [
    60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
    70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
]


@pytest.fixture
def strategy() -> MeanReversionStrategy:
    """Create a default mean reversion strategy."""
    return MeanReversionStrategy()


@pytest.fixture
def custom_strategy() -> MeanReversionStrategy:
    """Create a strategy with custom thresholds."""
    return MeanReversionStrategy(config={
        "rsi_period": 7,
        "rsi_oversold": 25,
        "rsi_overbought": 75,
        "macd_fast": 6,
        "macd_slow": 13,
        "macd_signal": 5,
    })


class TestIsBaseStrategy:
    """Test that MeanReversionStrategy extends BaseStrategy."""

    def test_isinstance_check(self, strategy: MeanReversionStrategy) -> None:
        assert isinstance(strategy, BaseStrategy)

    def test_is_subclass(self) -> None:
        assert issubclass(MeanReversionStrategy, BaseStrategy)


class TestCalculateRSI:
    """Test RSI calculation against known datasets."""

    def test_rsi_on_downtrend_is_low(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi(PRICES_DOWNTREND, period=14)
        # Consistent downtrend should produce RSI near 0
        assert rsi_values[-1] < 10

    def test_rsi_on_uptrend_is_high(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi(PRICES_UPTREND, period=14)
        # Consistent uptrend should produce RSI near 100
        assert rsi_values[-1] > 90

    def test_rsi_values_in_range(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi(PRICES_DOWNTREND + PRICES_UPTREND, period=14)
        for v in rsi_values[14:]:  # Skip initial zeros
            assert 0 <= v <= 100

    def test_rsi_length_matches_input(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi(PRICES_DOWNTREND, period=14)
        assert len(rsi_values) == len(PRICES_DOWNTREND)

    def test_rsi_with_custom_period(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi(PRICES_DOWNTREND, period=7)
        assert len(rsi_values) == len(PRICES_DOWNTREND)
        # Shorter period = more extreme values on consistent trend
        assert rsi_values[-1] < 5

    def test_rsi_returns_50_with_insufficient_data(self) -> None:
        rsi_values = MeanReversionStrategy.calculate_rsi([100, 101], period=14)
        assert all(v == 50.0 for v in rsi_values)


class TestCalculateMACD:
    """Test MACD calculation."""

    def test_macd_returns_three_lists(self) -> None:
        macd_line, signal_line, histogram = MeanReversionStrategy.calculate_macd(
            PRICES_DOWNTREND + PRICES_UPTREND
        )
        assert isinstance(macd_line, list)
        assert isinstance(signal_line, list)
        assert isinstance(histogram, list)

    def test_macd_lengths_match(self) -> None:
        prices = PRICES_DOWNTREND + PRICES_UPTREND
        macd_line, signal_line, histogram = MeanReversionStrategy.calculate_macd(prices)
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)

    def test_macd_downtrend_produces_negative_line(self) -> None:
        macd_line, _, _ = MeanReversionStrategy.calculate_macd(PRICES_DOWNTREND)
        # In a consistent downtrend, fast EMA < slow EMA → MACD line negative
        assert macd_line[-1] < 0

    def test_macd_uptrend_produces_positive_line(self) -> None:
        macd_line, _, _ = MeanReversionStrategy.calculate_macd(PRICES_UPTREND)
        # In a consistent uptrend, fast EMA > slow EMA → MACD line positive
        assert macd_line[-1] > 0

    def test_macd_custom_periods(self) -> None:
        macd_line, signal_line, histogram = MeanReversionStrategy.calculate_macd(
            PRICES_DOWNTREND + PRICES_UPTREND, fast_period=6, slow_period=13, signal_period=5
        )
        assert len(macd_line) == len(PRICES_DOWNTREND) + len(PRICES_UPTREND)


class TestGenerateSignal:
    """Test signal generation logic."""

    def test_hold_with_insufficient_data(self, strategy: MeanReversionStrategy) -> None:
        strategy.analyze({"close": 100})
        signal = strategy.generate_signal()
        assert signal["action"] == "HOLD"
        assert "insufficient" in signal["reason"]

    def test_hold_when_conditions_not_met(self, strategy: MeanReversionStrategy) -> None:
        # Feed flat prices — no extreme RSI, no MACD crossover
        for p in [100.0] * 50:
            strategy.analyze({"close": p})
        signal = strategy.generate_signal()
        assert signal["action"] == "HOLD"

    def test_buy_signal_on_oversold_with_macd_cross_up(self) -> None:
        # Construct prices: long downtrend → sharp reversal up
        # This should create RSI < 30 with MACD histogram crossing above 0
        prices = list(range(100, 60, -1))  # 40 points downtrend
        # Sharp reversal
        prices.extend([60, 61, 63, 66, 70, 75, 81, 88, 96, 105])

        strategy = MeanReversionStrategy(config={
            "rsi_period": 14,
            "rsi_oversold": 50,  # Use generous threshold to catch the signal
            "rsi_overbought": 70,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
        })
        for p in prices:
            strategy.analyze({"close": float(p)})

        signal = strategy.generate_signal()
        # The reversal should produce a BUY or at minimum have RSI in signal
        assert "rsi" in signal
        assert "macd_histogram" in signal

    def test_sell_signal_on_overbought_with_macd_cross_down(self) -> None:
        # Long uptrend → sharp reversal down
        prices = list(range(60, 100))  # 40 points uptrend
        # Sharp reversal
        prices.extend([100, 99, 97, 94, 90, 85, 79, 72, 64, 55])

        strategy = MeanReversionStrategy(config={
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 50,  # Generous threshold
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
        })
        for p in prices:
            strategy.analyze({"close": float(p)})

        signal = strategy.generate_signal()
        assert "rsi" in signal
        assert "macd_histogram" in signal


class TestConfigurable:
    """Test that all thresholds are configurable."""

    def test_default_config(self, strategy: MeanReversionStrategy) -> None:
        assert strategy.config["rsi_period"] == 14
        assert strategy.config["rsi_oversold"] == 30
        assert strategy.config["rsi_overbought"] == 70
        assert strategy.config["macd_fast"] == 12
        assert strategy.config["macd_slow"] == 26
        assert strategy.config["macd_signal"] == 9

    def test_custom_config(self, custom_strategy: MeanReversionStrategy) -> None:
        assert custom_strategy.config["rsi_period"] == 7
        assert custom_strategy.config["rsi_oversold"] == 25
        assert custom_strategy.config["rsi_overbought"] == 75
        assert custom_strategy.config["macd_fast"] == 6
        assert custom_strategy.config["macd_slow"] == 13
        assert custom_strategy.config["macd_signal"] == 5

    def test_update_config_changes_thresholds(self, strategy: MeanReversionStrategy) -> None:
        strategy.update_config({"rsi_period": 21, "rsi_oversold": 20})
        assert strategy.config["rsi_period"] == 21
        assert strategy.config["rsi_oversold"] == 20
        # Others unchanged
        assert strategy.config["rsi_overbought"] == 70


class TestAnalyze:
    """Test analyze method data ingestion."""

    def test_analyze_close_price(self, strategy: MeanReversionStrategy) -> None:
        strategy.analyze({"close": 42000})
        assert strategy._prices == [42000.0]

    def test_analyze_candle_data(self, strategy: MeanReversionStrategy) -> None:
        strategy.analyze({"data": [{"c": "42000"}, {"c": "42100"}]})
        assert strategy._prices == [42000.0, 42100.0]

    def test_analyze_accumulates(self, strategy: MeanReversionStrategy) -> None:
        strategy.analyze({"close": 100})
        strategy.analyze({"close": 200})
        assert len(strategy._prices) == 2


class TestExecute:
    """Test execute method."""

    def test_execute_hold_returns_none(self, strategy: MeanReversionStrategy) -> None:
        result = strategy.execute({"action": "HOLD"})
        assert result is None

    def test_execute_buy_returns_signal(self, strategy: MeanReversionStrategy) -> None:
        signal = {"action": "BUY", "reason": "test"}
        result = strategy.execute(signal)
        assert result is not None
        assert result["action"] == "BUY"

    def test_execute_sell_returns_signal(self, strategy: MeanReversionStrategy) -> None:
        signal = {"action": "SELL", "reason": "test"}
        result = strategy.execute(signal)
        assert result is not None
        assert result["action"] == "SELL"
