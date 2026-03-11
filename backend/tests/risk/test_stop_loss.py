"""Tests for Stop-loss automation."""

from __future__ import annotations

from typing import Any

import pytest

from src.risk.stop_loss import StopLossManager


def _pos(symbol: str = "BTC-USDT", entry_price: float = 100.0,
         current_price: float = 100.0, size: float = 0.1,
         side: str = "long") -> dict[str, Any]:
    """Helper to create a position dict."""
    return {
        "symbol": symbol, "entry_price": entry_price,
        "current_price": current_price, "size": size, "side": side,
    }


@pytest.fixture
def fixed_sl() -> StopLossManager:
    """Create a fixed-mode StopLossManager at 2%."""
    return StopLossManager(default_pct=2.0, mode="fixed")


@pytest.fixture
def trailing_sl() -> StopLossManager:
    """Create a trailing-mode StopLossManager at 2%."""
    return StopLossManager(default_pct=2.0, mode="trailing")


class TestInit:
    """Test constructor."""

    def test_stores_default_pct(self, fixed_sl: StopLossManager) -> None:
        assert fixed_sl._default_pct == 2.0

    def test_stores_mode(self, fixed_sl: StopLossManager) -> None:
        assert fixed_sl._mode == "fixed"


class TestCheckPositionsFixed:
    """Test check_positions with fixed stop-loss."""

    def test_no_trigger_above_stop(self, fixed_sl: StopLossManager) -> None:
        positions = [_pos(entry_price=100.0, current_price=99.0)]
        triggered = fixed_sl.check_positions(positions)
        assert len(triggered) == 0

    def test_triggers_at_stop_level(self, fixed_sl: StopLossManager) -> None:
        # Stop at 98.0 (100 * 0.98)
        positions = [_pos(entry_price=100.0, current_price=98.0)]
        triggered = fixed_sl.check_positions(positions)
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "BTC-USDT"

    def test_triggers_below_stop(self, fixed_sl: StopLossManager) -> None:
        positions = [_pos(entry_price=100.0, current_price=95.0)]
        triggered = fixed_sl.check_positions(positions)
        assert len(triggered) == 1

    def test_multiple_positions(self, fixed_sl: StopLossManager) -> None:
        positions = [
            _pos(symbol="BTC-USDT", entry_price=100.0, current_price=95.0),
            _pos(symbol="ETH-USDT", entry_price=100.0, current_price=99.5),
        ]
        triggered = fixed_sl.check_positions(positions)
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "BTC-USDT"


class TestCheckPositionsTrailing:
    """Test check_positions with trailing stop-loss."""

    def test_trailing_updates_stop_on_price_increase(self, trailing_sl: StopLossManager) -> None:
        # Entry at 100, price goes to 110 → stop should move to 110*0.98 = 107.8
        trailing_sl.check_positions([_pos(entry_price=100.0, current_price=110.0)])
        levels = trailing_sl.get_stop_levels()
        assert levels["BTC-USDT"]["stop_price"] == pytest.approx(107.8)
        assert levels["BTC-USDT"]["highest_price"] == 110.0

    def test_trailing_does_not_lower_stop(self, trailing_sl: StopLossManager) -> None:
        # Price goes up then down
        trailing_sl.check_positions([_pos(entry_price=100.0, current_price=110.0)])
        trailing_sl.check_positions([_pos(entry_price=100.0, current_price=108.0)])
        levels = trailing_sl.get_stop_levels()
        # Highest was 110, stop stays at 107.8
        assert levels["BTC-USDT"]["stop_price"] == pytest.approx(107.8)

    def test_trailing_triggers_after_peak(self, trailing_sl: StopLossManager) -> None:
        trailing_sl.check_positions([_pos(entry_price=100.0, current_price=110.0)])
        # Price drops below trailing stop (107.8)
        triggered = trailing_sl.check_positions([_pos(entry_price=100.0, current_price=107.0)])
        assert len(triggered) == 1


class TestSkipClosingPositions:
    """Test that positions already being closed are skipped."""

    def test_does_not_trigger_on_closing_position(self, fixed_sl: StopLossManager) -> None:
        positions = [_pos(entry_price=100.0, current_price=95.0)]
        # First call triggers
        triggered = fixed_sl.check_positions(positions)
        assert len(triggered) == 1

        # Second call should skip (already closing)
        triggered2 = fixed_sl.check_positions(positions)
        assert len(triggered2) == 0

    def test_mark_closed_allows_retrigger(self, fixed_sl: StopLossManager) -> None:
        positions = [_pos(entry_price=100.0, current_price=95.0)]
        fixed_sl.check_positions(positions)
        fixed_sl.mark_closed("BTC-USDT")

        # New position at same symbol can trigger again
        new_positions = [_pos(entry_price=90.0, current_price=85.0)]
        triggered = fixed_sl.check_positions(new_positions)
        assert len(triggered) == 1


class TestGetStopLevels:
    """Test get_stop_levels method."""

    def test_returns_empty_before_check(self, fixed_sl: StopLossManager) -> None:
        assert fixed_sl.get_stop_levels() == {}

    def test_returns_tracked_levels(self, fixed_sl: StopLossManager) -> None:
        fixed_sl.check_positions([_pos(entry_price=100.0, current_price=99.5)])
        levels = fixed_sl.get_stop_levels()
        assert "BTC-USDT" in levels
        assert levels["BTC-USDT"]["stop_price"] == pytest.approx(98.0)
        assert levels["BTC-USDT"]["entry_price"] == 100.0


class TestUpdateConfig:
    """Test hot-reload config."""

    def test_update_pct(self, fixed_sl: StopLossManager) -> None:
        fixed_sl.update_config(default_pct=5.0)
        assert fixed_sl._default_pct == 5.0

    def test_update_mode(self, fixed_sl: StopLossManager) -> None:
        fixed_sl.update_config(mode="trailing")
        assert fixed_sl._mode == "trailing"
