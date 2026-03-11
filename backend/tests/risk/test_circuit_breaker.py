"""Tests for Max drawdown circuit breaker."""

from __future__ import annotations

from typing import Any

import pytest

from src.risk.circuit_breaker import CircuitBreaker


@pytest.fixture
def cb() -> CircuitBreaker:
    """Create a circuit breaker with 5% threshold."""
    return CircuitBreaker(max_drawdown_pct=5.0)


class TestInit:
    """Test constructor stores threshold."""

    def test_stores_max_drawdown_pct(self, cb: CircuitBreaker) -> None:
        assert cb._max_drawdown_pct == 5.0

    def test_not_triggered_initially(self, cb: CircuitBreaker) -> None:
        assert cb.is_triggered() is False


class TestUpdate:
    """Test update method tracks peak equity and calculates drawdown."""

    def test_tracks_peak_equity(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(1100.0)
        assert cb._peak_equity == 1100.0

    def test_peak_does_not_decrease(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(900.0)
        assert cb._peak_equity == 1000.0

    def test_no_trigger_within_threshold(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(960.0)  # 4% drawdown, below 5%
        assert cb.is_triggered() is False

    def test_triggers_at_threshold(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(950.0)  # exactly 5%
        assert cb.is_triggered() is True

    def test_triggers_beyond_threshold(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(900.0)  # 10% drawdown
        assert cb.is_triggered() is True

    def test_sets_triggered_at_timestamp(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        assert cb._triggered_at is not None
        assert "T" in cb._triggered_at  # ISO format

    def test_does_not_retrigger_after_already_triggered(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)  # triggers
        first_ts = cb._triggered_at
        cb.update(930.0)  # further drop
        assert cb._triggered_at == first_ts  # timestamp unchanged


class TestIsTriggered:
    """Test is_triggered method."""

    def test_false_before_trigger(self, cb: CircuitBreaker) -> None:
        assert cb.is_triggered() is False

    def test_true_after_trigger(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        assert cb.is_triggered() is True


class TestReset:
    """Test reset method."""

    def test_clears_triggered_state(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        assert cb.is_triggered() is True

        cb.reset()
        assert cb.is_triggered() is False

    def test_resets_peak_to_current(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        cb.reset()
        assert cb._peak_equity == 940.0

    def test_resets_peak_to_provided_value(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        cb.reset(current_equity=950.0)
        assert cb._peak_equity == 950.0
        assert cb._current_equity == 950.0

    def test_clears_triggered_at(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        cb.reset()
        assert cb._triggered_at is None


class TestGetStatus:
    """Test get_status method."""

    def test_returns_correct_status_untriggered(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(980.0)
        status = cb.get_status()
        assert status["triggered"] is False
        assert status["peak_equity"] == 1000.0
        assert status["current_equity"] == 980.0
        assert status["drawdown_pct"] == 2.0
        assert status["max_drawdown_pct"] == 5.0

    def test_returns_correct_status_triggered(self, cb: CircuitBreaker) -> None:
        cb.update(1000.0)
        cb.update(940.0)
        status = cb.get_status()
        assert status["triggered"] is True
        assert status["drawdown_pct"] == 6.0
        assert status["triggered_at"] is not None

    def test_returns_zero_drawdown_initially(self, cb: CircuitBreaker) -> None:
        status = cb.get_status()
        assert status["drawdown_pct"] == 0.0


class TestUpdateConfig:
    """Test hot-reload threshold."""

    def test_update_threshold(self, cb: CircuitBreaker) -> None:
        cb.update_config(max_drawdown_pct=10.0)
        assert cb._max_drawdown_pct == 10.0

    def test_new_threshold_affects_trigger(self, cb: CircuitBreaker) -> None:
        cb.update_config(max_drawdown_pct=10.0)
        cb.update(1000.0)
        cb.update(920.0)  # 8% drawdown, below new 10% threshold
        assert cb.is_triggered() is False
