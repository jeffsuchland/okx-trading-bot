"""Strategy registry for runtime strategy switching."""

from __future__ import annotations

from typing import Type

from src.strategies.base_strategy import BaseStrategy


class StrategyRegistry:
    """Registry that maps string names to strategy classes for runtime lookup."""

    def __init__(self) -> None:
        self._strategies: dict[str, Type[BaseStrategy]] = {}

    def register(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a strategy class under a given name.

        Args:
            name: Unique string identifier for the strategy.
            strategy_class: A subclass of BaseStrategy.

        Raises:
            TypeError: If strategy_class is not a subclass of BaseStrategy.
        """
        if not (isinstance(strategy_class, type) and issubclass(strategy_class, BaseStrategy)):
            raise TypeError(f"{strategy_class} is not a subclass of BaseStrategy")
        self._strategies[name] = strategy_class

    def get(self, name: str) -> Type[BaseStrategy]:
        """Retrieve a registered strategy class by name.

        Args:
            name: The registered name of the strategy.

        Returns:
            The strategy class.

        Raises:
            KeyError: If no strategy is registered under that name.
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found. Available: {list(self._strategies.keys())}")
        return self._strategies[name]

    def list_strategies(self) -> list[str]:
        """Return all registered strategy names."""
        return list(self._strategies.keys())
