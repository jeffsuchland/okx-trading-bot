"""Abstract base class for trading strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Abstract base class that all trading strategies must extend.

    Subclasses must implement analyze(), generate_signal(), and execute().
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

    @abstractmethod
    def analyze(self, market_data: dict[str, Any]) -> None:
        """Analyze incoming market data and update internal state.

        Args:
            market_data: Parsed market data from WebSocket (ticker, candles, etc.)
        """

    @abstractmethod
    def generate_signal(self) -> dict[str, Any]:
        """Generate a trading signal based on the current analysis.

        Returns:
            A signal dict, e.g. {"action": "BUY"|"SELL"|"HOLD", ...}
        """

    @abstractmethod
    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        """Execute a trading signal via the order manager.

        Args:
            signal: The signal dict from generate_signal().

        Returns:
            Execution result or None if no action taken.
        """

    def get_config(self) -> dict[str, Any]:
        """Return the current strategy configuration."""
        return dict(self.config)

    def update_config(self, new_config: dict[str, Any]) -> None:
        """Hot-reload strategy parameters."""
        self.config.update(new_config)
