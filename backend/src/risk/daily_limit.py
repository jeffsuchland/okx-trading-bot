"""Daily loss limit guard to pause trading when daily losses exceed threshold."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DailyLimitGuard:
    """Tracks cumulative realized loss for the current UTC day.

    Pauses trading when daily losses exceed the configured limit.
    Automatically resets at UTC midnight.
    """

    def __init__(self, max_daily_loss_usdt: float = 50.0) -> None:
        self._max_daily_loss = max_daily_loss_usdt
        self._is_halted = False
        self._last_check_date: str = self._today()

    @staticmethod
    def _today() -> str:
        """Return current UTC date as YYYY-MM-DD string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _check_day_rollover(self) -> None:
        """Auto-reset if we've crossed into a new UTC day."""
        today = self._today()
        if today != self._last_check_date:
            self._is_halted = False
            self._last_check_date = today
            logger.info("Daily limit guard reset for new day: %s", today)

    def check(self, daily_pnl: float) -> bool:
        """Check if daily loss is within the limit.

        Args:
            daily_pnl: The cumulative realized PnL for today (negative = loss).

        Returns:
            True if safe to continue trading, False if halted.
        """
        self._check_day_rollover()

        if self._is_halted:
            return False

        # daily_pnl is negative when losing; compare absolute loss to limit
        if daily_pnl < 0 and abs(daily_pnl) >= self._max_daily_loss:
            self._is_halted = True
            logger.warning(
                "DAILY LOSS LIMIT HIT: loss=%.2f >= limit=%.2f. Trading paused.",
                abs(daily_pnl),
                self._max_daily_loss,
            )
            return False

        return True

    def get_status(self) -> dict[str, Any]:
        """Return current daily loss state."""
        self._check_day_rollover()
        return {
            "is_halted": self._is_halted,
            "max_daily_loss": self._max_daily_loss,
            "date": self._last_check_date,
        }

    def update_config(self, max_daily_loss_usdt: float | None = None) -> None:
        """Hot-reload daily loss limit."""
        if max_daily_loss_usdt is not None:
            self._max_daily_loss = max_daily_loss_usdt
            logger.info("Daily loss limit updated to %.2f USDT", self._max_daily_loss)

    def reset(self) -> None:
        """Manually reset the halted state."""
        self._is_halted = False
        logger.info("Daily limit guard manually reset")
