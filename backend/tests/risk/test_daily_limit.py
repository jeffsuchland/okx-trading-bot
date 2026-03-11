"""Tests for Daily loss limit guard."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.risk.daily_limit import DailyLimitGuard


@pytest.fixture
def guard() -> DailyLimitGuard:
    """Create a DailyLimitGuard with $50 limit."""
    return DailyLimitGuard(max_daily_loss_usdt=50.0)


class TestInit:
    """Test constructor stores daily limit."""

    def test_stores_max_daily_loss(self, guard: DailyLimitGuard) -> None:
        assert guard._max_daily_loss == 50.0

    def test_not_halted_initially(self, guard: DailyLimitGuard) -> None:
        assert guard._is_halted is False


class TestCheckSafe:
    """Test check returns True when daily loss is within limit."""

    def test_safe_with_positive_pnl(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=10.0) is True

    def test_safe_with_zero_pnl(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=0.0) is True

    def test_safe_with_small_loss(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=-30.0) is True

    def test_safe_just_below_limit(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=-49.99) is True


class TestCheckHalt:
    """Test check returns False when daily loss exceeds limit."""

    def test_halts_at_limit(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=-50.0) is False

    def test_halts_beyond_limit(self, guard: DailyLimitGuard) -> None:
        assert guard.check(daily_pnl=-75.0) is False

    def test_stays_halted_once_triggered(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        # Even if PnL recovers, guard stays halted until reset
        assert guard.check(daily_pnl=-10.0) is False

    def test_stays_halted_with_positive_pnl(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-55.0)
        assert guard.check(daily_pnl=5.0) is False


class TestAutoResetAtMidnight:
    """Test automatic reset at UTC midnight."""

    def test_resets_on_new_day(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        assert guard._is_halted is True

        # Simulate day change
        with patch.object(DailyLimitGuard, "_today", return_value="2099-01-02"):
            result = guard.check(daily_pnl=-10.0)
            assert result is True
            assert guard._is_halted is False

    def test_no_reset_same_day(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        # Same day, still halted
        result = guard.check(daily_pnl=-10.0)
        assert result is False


class TestGetStatus:
    """Test get_status method."""

    def test_returns_correct_status_not_halted(self, guard: DailyLimitGuard) -> None:
        status = guard.get_status()
        assert status["is_halted"] is False
        assert status["max_daily_loss"] == 50.0
        assert "date" in status

    def test_returns_correct_status_halted(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        status = guard.get_status()
        assert status["is_halted"] is True


class TestUpdateConfig:
    """Test hot-reload config."""

    def test_update_max_daily_loss(self, guard: DailyLimitGuard) -> None:
        guard.update_config(max_daily_loss_usdt=100.0)
        assert guard._max_daily_loss == 100.0

    def test_new_limit_affects_check(self, guard: DailyLimitGuard) -> None:
        guard.update_config(max_daily_loss_usdt=100.0)
        # -60 is now within the new $100 limit
        assert guard.check(daily_pnl=-60.0) is True


class TestManualReset:
    """Test manual reset."""

    def test_reset_clears_halted(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        assert guard._is_halted is True
        guard.reset()
        assert guard._is_halted is False

    def test_can_trade_after_reset(self, guard: DailyLimitGuard) -> None:
        guard.check(daily_pnl=-60.0)
        guard.reset()
        assert guard.check(daily_pnl=-10.0) is True
