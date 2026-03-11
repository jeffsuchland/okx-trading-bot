"""Tests for Grid trading strategy."""

from __future__ import annotations

from typing import Any

import pytest

from src.strategies.base_strategy import BaseStrategy
from src.strategies.grid_trading import GridTradingStrategy


@pytest.fixture
def strategy() -> GridTradingStrategy:
    """Create a default grid trading strategy."""
    return GridTradingStrategy()


@pytest.fixture
def custom_strategy() -> GridTradingStrategy:
    """Create a strategy with custom config."""
    return GridTradingStrategy(config={
        "num_levels": 3,
        "spacing_pct": 1.0,
        "order_size_usdt": 20.0,
    })


class TestIsBaseStrategy:
    """Test that GridTradingStrategy extends BaseStrategy."""

    def test_isinstance_check(self, strategy: GridTradingStrategy) -> None:
        assert isinstance(strategy, BaseStrategy)

    def test_is_subclass(self) -> None:
        assert issubclass(GridTradingStrategy, BaseStrategy)


class TestCalculateGridLevels:
    """Test calculate_grid_levels static method."""

    def test_returns_buy_and_sell_arrays(self) -> None:
        buy_levels, sell_levels = GridTradingStrategy.calculate_grid_levels(100.0, 5, 0.5)
        assert isinstance(buy_levels, list)
        assert isinstance(sell_levels, list)
        assert len(buy_levels) == 5
        assert len(sell_levels) == 5

    def test_buy_levels_below_price(self) -> None:
        buy_levels, _ = GridTradingStrategy.calculate_grid_levels(100.0, 3, 1.0)
        for level in buy_levels:
            assert level < 100.0

    def test_sell_levels_above_price(self) -> None:
        _, sell_levels = GridTradingStrategy.calculate_grid_levels(100.0, 3, 1.0)
        for level in sell_levels:
            assert level > 100.0

    def test_levels_are_evenly_spaced(self) -> None:
        buy_levels, sell_levels = GridTradingStrategy.calculate_grid_levels(1000.0, 3, 1.0)
        # Buy levels: 990, 980, 970
        assert buy_levels[0] == pytest.approx(990.0)
        assert buy_levels[1] == pytest.approx(980.0)
        assert buy_levels[2] == pytest.approx(970.0)
        # Sell levels: 1010, 1020, 1030
        assert sell_levels[0] == pytest.approx(1010.0)
        assert sell_levels[1] == pytest.approx(1020.0)
        assert sell_levels[2] == pytest.approx(1030.0)

    def test_different_spacing(self) -> None:
        buy_levels, sell_levels = GridTradingStrategy.calculate_grid_levels(100.0, 2, 2.0)
        assert buy_levels[0] == pytest.approx(98.0)
        assert buy_levels[1] == pytest.approx(96.0)
        assert sell_levels[0] == pytest.approx(102.0)
        assert sell_levels[1] == pytest.approx(104.0)


class TestGenerateSignal:
    """Test signal generation."""

    def test_hold_without_price_data(self, strategy: GridTradingStrategy) -> None:
        signal = strategy.generate_signal()
        assert signal["action"] == "HOLD"
        assert signal["orders"] == []

    def test_generates_grid_orders_on_first_price(self, strategy: GridTradingStrategy) -> None:
        strategy.analyze({"last": 42000.0})
        signal = strategy.generate_signal()
        assert signal["action"] == "GRID"
        assert len(signal["orders"]) == 10  # 5 buy + 5 sell
        assert signal["grid_center"] == 42000.0

    def test_orders_have_correct_structure(self, strategy: GridTradingStrategy) -> None:
        strategy.analyze({"last": 100.0})
        signal = strategy.generate_signal()
        for order in signal["orders"]:
            assert "side" in order
            assert "price" in order
            assert "qty" in order
            assert order["side"] in ("buy", "sell")
            assert order["qty"] > 0

    def test_no_duplicate_orders_on_second_call(self, strategy: GridTradingStrategy) -> None:
        strategy.analyze({"last": 100.0})
        signal1 = strategy.generate_signal()
        assert len(signal1["orders"]) == 10

        # Same price, same grid — no new orders
        signal2 = strategy.generate_signal()
        assert signal2["action"] == "HOLD"
        assert signal2["orders"] == []

    def test_custom_num_levels(self, custom_strategy: GridTradingStrategy) -> None:
        custom_strategy.analyze({"last": 100.0})
        signal = custom_strategy.generate_signal()
        assert len(signal["orders"]) == 6  # 3 buy + 3 sell


class TestGridRebalance:
    """Test grid rebalancing when price moves outside range."""

    def test_rebalances_when_price_moves_beyond_grid(self) -> None:
        strategy = GridTradingStrategy(config={
            "num_levels": 3,
            "spacing_pct": 1.0,
            "order_size_usdt": 10.0,
        })
        # Initial grid around 100
        strategy.analyze({"last": 100.0})
        signal1 = strategy.generate_signal()
        assert signal1["action"] == "GRID"
        assert signal1["grid_center"] == 100.0

        # Price moves well beyond the outermost level (3% away, grid only covers 3%)
        strategy.analyze({"last": 110.0})
        signal2 = strategy.generate_signal()
        assert signal2["action"] == "GRID"
        assert signal2["grid_center"] == 110.0
        assert len(signal2["orders"]) == 6  # Full new grid

    def test_no_rebalance_within_grid_range(self) -> None:
        strategy = GridTradingStrategy(config={
            "num_levels": 5,
            "spacing_pct": 1.0,
            "order_size_usdt": 10.0,
        })
        strategy.analyze({"last": 100.0})
        strategy.generate_signal()

        # Small move, still within grid
        strategy.analyze({"last": 101.0})
        signal = strategy.generate_signal()
        assert signal["action"] == "HOLD"


class TestConfigurable:
    """Test configurable parameters."""

    def test_default_config(self, strategy: GridTradingStrategy) -> None:
        assert strategy.config["num_levels"] == 5
        assert strategy.config["spacing_pct"] == 0.5
        assert strategy.config["order_size_usdt"] == 10.0

    def test_custom_config(self, custom_strategy: GridTradingStrategy) -> None:
        assert custom_strategy.config["num_levels"] == 3
        assert custom_strategy.config["spacing_pct"] == 1.0
        assert custom_strategy.config["order_size_usdt"] == 20.0

    def test_update_config(self, strategy: GridTradingStrategy) -> None:
        strategy.update_config({"num_levels": 10})
        assert strategy.config["num_levels"] == 10


class TestNoDuplicateOrders:
    """Test that duplicate orders at existing levels are prevented."""

    def test_active_levels_tracked(self, strategy: GridTradingStrategy) -> None:
        strategy.analyze({"last": 100.0})
        strategy.generate_signal()
        assert len(strategy._active_levels) == 10

    def test_no_orders_at_existing_levels(self, strategy: GridTradingStrategy) -> None:
        strategy.analyze({"last": 100.0})
        strategy.generate_signal()

        # Second call with same center should produce no new orders
        signal = strategy.generate_signal()
        assert signal["orders"] == []


class TestExecute:
    """Test execute method."""

    def test_execute_hold_returns_none(self, strategy: GridTradingStrategy) -> None:
        result = strategy.execute({"action": "HOLD", "orders": []})
        assert result is None

    def test_execute_grid_returns_signal(self, strategy: GridTradingStrategy) -> None:
        signal = {"action": "GRID", "orders": [{"side": "buy", "price": 99.5, "qty": 0.1}]}
        result = strategy.execute(signal)
        assert result is not None
        assert result["action"] == "GRID"
