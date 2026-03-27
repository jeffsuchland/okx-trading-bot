"""Risk manager orchestrator coordinating all risk sub-components."""

from __future__ import annotations

import logging
from typing import Any

from src.risk.circuit_breaker import CircuitBreaker
from src.risk.daily_limit import DailyLimitGuard
from src.risk.position_sizer import PositionSizer
from src.risk.stop_loss import StopLossManager

logger = logging.getLogger(__name__)


class RiskManager:
    """Orchestrates all risk components and provides a unified interface.

    Called by the TradingLoop before and after every trade execution.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._position_sizer = PositionSizer(
            spend_per_trade=float(cfg.get("spend_per_trade", 10.0)),
            max_total_exposure=float(cfg.get("max_total_exposure", 100.0)),
        )
        self._stop_loss = StopLossManager(
            default_pct=float(cfg.get("stop_loss_pct", 2.0)),
            mode=str(cfg.get("stop_loss_mode", "fixed")),
        )
        self._circuit_breaker = CircuitBreaker(
            max_drawdown_pct=float(cfg.get("max_drawdown_pct", 5.0)),
        )
        self._daily_limit = DailyLimitGuard(
            max_daily_loss_usdt=float(cfg.get("max_daily_loss", 50.0)),
        )
        self._order_manager: Any = None
        self._halted = False

    def set_order_manager(self, order_manager: Any) -> None:
        """Inject the OrderManager reference (avoids circular dependency)."""
        self._order_manager = order_manager

    def pre_trade_check(self, signal: dict[str, Any]) -> tuple[bool, str]:
        """Run all risk checks before executing a trade.

        Args:
            signal: The trading signal dict with at least 'action' and 'price'.

        Returns:
            Tuple of (approved, reason).
        """
        if self._halted:
            return False, "risk manager is halted (panic mode)"

        if self._circuit_breaker.is_triggered():
            return False, "circuit breaker triggered"

        daily_pnl = signal.get("daily_pnl", 0.0)
        if not self._daily_limit.check(daily_pnl):
            return False, "daily loss limit exceeded"

        price = float(signal.get("price", 0))
        if price > 0:
            qty = self._position_sizer.calculate_qty(price)
            if qty == 0:
                return False, "position sizing: max exposure would be exceeded"

        return True, "approved"

    def post_trade_update(self, trade_result: dict[str, Any]) -> None:
        """Update risk state after a trade execution.

        Args:
            trade_result: Dict with keys: side, qty, price, fee, pnl, symbol, current_equity.
        """
        self._position_sizer.update_exposure(trade_result)

        current_equity = float(trade_result.get("current_equity", 0))
        if current_equity > 0:
            self._circuit_breaker.update(current_equity)

    def check_stop_losses(self, positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check all positions against stop-loss levels.

        Args:
            positions: List of position dicts.

        Returns:
            List of positions that triggered stop-loss.
        """
        return self._stop_loss.check_positions(positions)

    def get_risk_status(self) -> dict[str, Any]:
        """Return a unified status dict for the dashboard."""
        return {
            "halted": self._halted,
            "spend_per_trade": self._position_sizer._spend_per_trade,
            "max_total_exposure": self._position_sizer._max_total_exposure,
            "stop_loss_pct": self._stop_loss._default_pct,
            "current_exposure": self._position_sizer.get_current_exposure(),
            "circuit_breaker": self._circuit_breaker.get_status(),
            "daily_limit": self._daily_limit.get_status(),
            "stop_loss_levels": self._stop_loss.get_stop_levels(),
        }

    def update_config(self, new_config: dict[str, Any]) -> None:
        """Hot-reload all risk parameters without restart."""
        if "spend_per_trade" in new_config or "max_total_exposure" in new_config:
            self._position_sizer.update_config(
                spend_per_trade=new_config.get("spend_per_trade"),
                max_total_exposure=new_config.get("max_total_exposure"),
            )
        if "stop_loss_pct" in new_config or "stop_loss_mode" in new_config:
            self._stop_loss.update_config(
                default_pct=new_config.get("stop_loss_pct"),
                mode=new_config.get("stop_loss_mode"),
            )
        if "max_drawdown_pct" in new_config:
            self._circuit_breaker.update_config(
                max_drawdown_pct=new_config.get("max_drawdown_pct"),
            )
        if "max_daily_loss" in new_config:
            self._daily_limit.update_config(
                max_daily_loss_usdt=new_config.get("max_daily_loss"),
            )
        logger.info("Risk config updated: %s", list(new_config.keys()))

    def panic(self) -> None:
        """Enter panic mode: flatten all positions and halt risk components."""
        self._halted = True
        if self._order_manager is not None:
            self._order_manager.panic_flatten()
        logger.warning("PANIC MODE ACTIVATED — all trading halted")

    def reset(self) -> None:
        """Reset panic/halt state."""
        self._halted = False
        logger.info("Risk manager reset from panic mode")
