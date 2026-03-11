"""Max drawdown circuit breaker for account equity protection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Monitors account equity and halts trading when drawdown exceeds threshold.

    Once triggered, requires manual reset via the dashboard.
    """

    def __init__(self, max_drawdown_pct: float = 5.0) -> None:
        self._max_drawdown_pct = max_drawdown_pct
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        self._triggered = False
        self._triggered_at: str | None = None

    def update(self, current_equity: float) -> None:
        """Update with current equity and check for drawdown breach.

        Args:
            current_equity: Current total account equity in USDT.
        """
        self._current_equity = current_equity

        if current_equity > self._peak_equity:
            self._peak_equity = current_equity

        if self._peak_equity > 0 and not self._triggered:
            drawdown_pct = ((self._peak_equity - current_equity) / self._peak_equity) * 100
            if drawdown_pct >= self._max_drawdown_pct:
                self._triggered = True
                self._triggered_at = datetime.now(timezone.utc).isoformat()
                logger.warning(
                    "CIRCUIT BREAKER TRIGGERED: peak=%.2f, current=%.2f, drawdown=%.2f%%",
                    self._peak_equity,
                    current_equity,
                    drawdown_pct,
                )

    def is_triggered(self) -> bool:
        """Return True if the circuit breaker has been triggered."""
        return self._triggered

    def reset(self, current_equity: float | None = None) -> None:
        """Clear the triggered state and reset peak equity.

        Args:
            current_equity: If provided, sets new peak to this value. Otherwise uses last known.
        """
        self._triggered = False
        self._triggered_at = None
        if current_equity is not None:
            self._peak_equity = current_equity
            self._current_equity = current_equity
        else:
            self._peak_equity = self._current_equity
        logger.info("Circuit breaker reset. Peak equity set to %.2f", self._peak_equity)

    def get_status(self) -> dict[str, Any]:
        """Return current drawdown percentage and triggered state."""
        if self._peak_equity > 0:
            drawdown_pct = ((self._peak_equity - self._current_equity) / self._peak_equity) * 100
        else:
            drawdown_pct = 0.0

        return {
            "triggered": self._triggered,
            "triggered_at": self._triggered_at,
            "peak_equity": self._peak_equity,
            "current_equity": self._current_equity,
            "drawdown_pct": round(drawdown_pct, 2),
            "max_drawdown_pct": self._max_drawdown_pct,
        }

    def update_config(self, max_drawdown_pct: float | None = None) -> None:
        """Hot-reload circuit breaker threshold."""
        if max_drawdown_pct is not None:
            self._max_drawdown_pct = max_drawdown_pct
            logger.info("CircuitBreaker threshold updated to %.2f%%", self._max_drawdown_pct)
