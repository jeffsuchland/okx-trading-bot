"""Tests for Risk manager orchestrator."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.risk.risk_manager import RiskManager


@pytest.fixture
def config() -> dict[str, Any]:
    return {
        "spend_per_trade": 10.0,
        "max_total_exposure": 100.0,
        "stop_loss_pct": 2.0,
        "stop_loss_mode": "fixed",
        "max_drawdown_pct": 5.0,
        "max_daily_loss": 50.0,
    }


@pytest.fixture
def rm(config: dict[str, Any]) -> RiskManager:
    return RiskManager(config=config)


@pytest.fixture
def rm_with_om(rm: RiskManager) -> RiskManager:
    mock_om = MagicMock()
    rm.set_order_manager(mock_om)
    return rm


class TestInit:
    """Test constructor instantiates all sub-components from config."""

    def test_creates_position_sizer(self, rm: RiskManager) -> None:
        assert rm._position_sizer._spend_per_trade == 10.0
        assert rm._position_sizer._max_total_exposure == 100.0

    def test_creates_stop_loss(self, rm: RiskManager) -> None:
        assert rm._stop_loss._default_pct == 2.0
        assert rm._stop_loss._mode == "fixed"

    def test_creates_circuit_breaker(self, rm: RiskManager) -> None:
        assert rm._circuit_breaker._max_drawdown_pct == 5.0

    def test_creates_daily_limit(self, rm: RiskManager) -> None:
        assert rm._daily_limit._max_daily_loss == 50.0

    def test_default_config(self) -> None:
        rm = RiskManager()
        assert rm._position_sizer._spend_per_trade == 10.0


class TestPreTradeCheck:
    """Test pre_trade_check returns (approved, reason)."""

    def test_approved_normal(self, rm: RiskManager) -> None:
        approved, reason = rm.pre_trade_check({"action": "BUY", "price": 100.0})
        assert approved is True
        assert reason == "approved"

    def test_blocked_by_circuit_breaker(self, rm: RiskManager) -> None:
        rm._circuit_breaker.update(1000.0)
        rm._circuit_breaker.update(940.0)  # 6% drawdown triggers
        approved, reason = rm.pre_trade_check({"action": "BUY", "price": 100.0})
        assert approved is False
        assert "circuit breaker" in reason

    def test_blocked_by_daily_limit(self, rm: RiskManager) -> None:
        approved, reason = rm.pre_trade_check({"action": "BUY", "price": 100.0, "daily_pnl": -60.0})
        assert approved is False
        assert "daily loss" in reason

    def test_blocked_by_position_sizing(self, rm: RiskManager) -> None:
        rm._position_sizer._current_exposure = 95.0
        approved, reason = rm.pre_trade_check({"action": "BUY", "price": 100.0})
        assert approved is False
        assert "exposure" in reason

    def test_blocked_when_halted(self, rm: RiskManager) -> None:
        rm._halted = True
        approved, reason = rm.pre_trade_check({"action": "BUY", "price": 100.0})
        assert approved is False
        assert "halted" in reason


class TestPostTradeUpdate:
    """Test post_trade_update updates exposure and circuit breaker."""

    def test_updates_exposure(self, rm: RiskManager) -> None:
        rm.post_trade_update({"side": "buy", "qty": 0.1, "price": 100.0, "current_equity": 1000.0})
        assert rm._position_sizer.get_current_exposure() == pytest.approx(10.0)

    def test_updates_circuit_breaker(self, rm: RiskManager) -> None:
        rm.post_trade_update({"side": "buy", "qty": 0.1, "price": 100.0, "current_equity": 1000.0})
        assert rm._circuit_breaker._peak_equity == 1000.0


class TestCheckStopLosses:
    """Test check_stop_losses delegates to StopLossManager."""

    def test_returns_triggered_positions(self, rm: RiskManager) -> None:
        positions = [{"symbol": "BTC-USDT", "entry_price": 100.0, "current_price": 95.0, "size": 0.1, "side": "long"}]
        triggered = rm.check_stop_losses(positions)
        assert len(triggered) == 1

    def test_returns_empty_when_no_trigger(self, rm: RiskManager) -> None:
        positions = [{"symbol": "BTC-USDT", "entry_price": 100.0, "current_price": 99.5, "size": 0.1, "side": "long"}]
        triggered = rm.check_stop_losses(positions)
        assert len(triggered) == 0


class TestGetRiskStatus:
    """Test get_risk_status returns unified dict."""

    def test_returns_all_fields(self, rm: RiskManager) -> None:
        status = rm.get_risk_status()
        assert "halted" in status
        assert "current_exposure" in status
        assert "circuit_breaker" in status
        assert "daily_limit" in status
        assert "stop_loss_levels" in status

    def test_reflects_state(self, rm: RiskManager) -> None:
        rm._position_sizer._current_exposure = 42.0
        status = rm.get_risk_status()
        assert status["current_exposure"] == 42.0
        assert status["halted"] is False


class TestUpdateConfig:
    """Test hot-reload of all risk parameters."""

    def test_updates_position_sizer(self, rm: RiskManager) -> None:
        rm.update_config({"spend_per_trade": 20.0, "max_total_exposure": 200.0})
        assert rm._position_sizer._spend_per_trade == 20.0
        assert rm._position_sizer._max_total_exposure == 200.0

    def test_updates_stop_loss(self, rm: RiskManager) -> None:
        rm.update_config({"stop_loss_pct": 5.0, "stop_loss_mode": "trailing"})
        assert rm._stop_loss._default_pct == 5.0
        assert rm._stop_loss._mode == "trailing"

    def test_updates_circuit_breaker(self, rm: RiskManager) -> None:
        rm.update_config({"max_drawdown_pct": 10.0})
        assert rm._circuit_breaker._max_drawdown_pct == 10.0

    def test_updates_daily_limit(self, rm: RiskManager) -> None:
        rm.update_config({"max_daily_loss": 100.0})
        assert rm._daily_limit._max_daily_loss == 100.0

    def test_partial_update(self, rm: RiskManager) -> None:
        rm.update_config({"spend_per_trade": 25.0})
        assert rm._position_sizer._spend_per_trade == 25.0
        # Others unchanged
        assert rm._stop_loss._default_pct == 2.0


class TestPanic:
    """Test panic mode delegates to OrderManager and halts."""

    async def test_panic_sets_halted(self, rm: RiskManager) -> None:
        await rm.panic()
        assert rm._halted is True

    async def test_panic_calls_order_manager(self, rm_with_om: RiskManager) -> None:
        from unittest.mock import AsyncMock
        rm_with_om._order_manager.panic_flatten = AsyncMock()
        await rm_with_om.panic()
        rm_with_om._order_manager.panic_flatten.assert_called_once()

    async def test_panic_without_order_manager(self, rm: RiskManager) -> None:
        # Should not raise even without order manager
        await rm.panic()
        assert rm._halted is True

    async def test_reset_clears_halted(self, rm: RiskManager) -> None:
        await rm.panic()
        rm.reset()
        assert rm._halted is False
