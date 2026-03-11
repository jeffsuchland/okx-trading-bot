"""Tests for Position sizing engine."""

from __future__ import annotations

import pytest

from src.risk.position_sizer import PositionSizer


@pytest.fixture
def sizer() -> PositionSizer:
    """Create a default PositionSizer."""
    return PositionSizer(spend_per_trade=10.0, max_total_exposure=100.0)


class TestInit:
    """Test constructor stores configurable limits."""

    def test_stores_spend_per_trade(self, sizer: PositionSizer) -> None:
        assert sizer._spend_per_trade == 10.0

    def test_stores_max_total_exposure(self, sizer: PositionSizer) -> None:
        assert sizer._max_total_exposure == 100.0

    def test_initial_exposure_is_zero(self, sizer: PositionSizer) -> None:
        assert sizer.get_current_exposure() == 0.0


class TestCalculateQty:
    """Test calculate_qty method."""

    def test_returns_qty_based_on_spend(self, sizer: PositionSizer) -> None:
        qty = sizer.calculate_qty(price=50000.0)
        assert qty == pytest.approx(10.0 / 50000.0)

    def test_returns_qty_at_lower_price(self, sizer: PositionSizer) -> None:
        qty = sizer.calculate_qty(price=100.0)
        assert qty == pytest.approx(0.1)

    def test_returns_zero_when_exceeds_max_exposure(self, sizer: PositionSizer) -> None:
        sizer._current_exposure = 95.0
        qty = sizer.calculate_qty(price=100.0)
        assert qty == 0.0

    def test_returns_zero_at_exact_max(self, sizer: PositionSizer) -> None:
        sizer._current_exposure = 90.0
        # 90 + 10 = 100, exactly at max — should be allowed
        qty = sizer.calculate_qty(price=100.0)
        assert qty == pytest.approx(0.1)

    def test_returns_zero_for_zero_price(self, sizer: PositionSizer) -> None:
        assert sizer.calculate_qty(price=0.0) == 0.0

    def test_returns_zero_for_negative_price(self, sizer: PositionSizer) -> None:
        assert sizer.calculate_qty(price=-10.0) == 0.0

    def test_uses_override_exposure(self, sizer: PositionSizer) -> None:
        # Internal exposure is 0, but override says 95
        qty = sizer.calculate_qty(price=100.0, current_exposure=95.0)
        assert qty == 0.0


class TestUpdateExposure:
    """Test update_exposure method."""

    def test_buy_increases_exposure(self, sizer: PositionSizer) -> None:
        sizer.update_exposure({"side": "buy", "qty": 0.001, "price": 50000.0})
        assert sizer.get_current_exposure() == pytest.approx(50.0)

    def test_sell_decreases_exposure(self, sizer: PositionSizer) -> None:
        sizer._current_exposure = 100.0
        sizer.update_exposure({"side": "sell", "qty": 0.001, "price": 50000.0})
        assert sizer.get_current_exposure() == pytest.approx(50.0)

    def test_sell_does_not_go_negative(self, sizer: PositionSizer) -> None:
        sizer._current_exposure = 10.0
        sizer.update_exposure({"side": "sell", "qty": 1.0, "price": 50000.0})
        assert sizer.get_current_exposure() == 0.0

    def test_multiple_buys_accumulate(self, sizer: PositionSizer) -> None:
        sizer.update_exposure({"side": "buy", "qty": 0.1, "price": 100.0})
        sizer.update_exposure({"side": "buy", "qty": 0.2, "price": 100.0})
        assert sizer.get_current_exposure() == pytest.approx(30.0)


class TestGetCurrentExposure:
    """Test get_current_exposure method."""

    def test_returns_tracked_exposure(self, sizer: PositionSizer) -> None:
        sizer._current_exposure = 42.5
        assert sizer.get_current_exposure() == 42.5


class TestUpdateConfig:
    """Test hot-reload via update_config."""

    def test_update_spend_per_trade(self, sizer: PositionSizer) -> None:
        sizer.update_config(spend_per_trade=20.0)
        assert sizer._spend_per_trade == 20.0

    def test_update_max_total_exposure(self, sizer: PositionSizer) -> None:
        sizer.update_config(max_total_exposure=500.0)
        assert sizer._max_total_exposure == 500.0

    def test_update_both(self, sizer: PositionSizer) -> None:
        sizer.update_config(spend_per_trade=25.0, max_total_exposure=250.0)
        assert sizer._spend_per_trade == 25.0
        assert sizer._max_total_exposure == 250.0

    def test_partial_update_preserves_other(self, sizer: PositionSizer) -> None:
        sizer.update_config(spend_per_trade=15.0)
        assert sizer._spend_per_trade == 15.0
        assert sizer._max_total_exposure == 100.0  # unchanged

    def test_new_config_affects_calculation(self, sizer: PositionSizer) -> None:
        sizer.update_config(spend_per_trade=50.0, max_total_exposure=200.0)
        qty = sizer.calculate_qty(price=100.0)
        assert qty == pytest.approx(0.5)
