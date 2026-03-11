"""Tests for StrategyRegistry."""

from __future__ import annotations

from typing import Any

import pytest

from src.strategies.base_strategy import BaseStrategy
from src.strategies.registry import StrategyRegistry


class FakeStrategyA(BaseStrategy):
    def analyze(self, market_data: dict[str, Any]) -> None:
        pass

    def generate_signal(self) -> dict[str, Any]:
        return {"action": "HOLD"}

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        return None


class FakeStrategyB(BaseStrategy):
    def analyze(self, market_data: dict[str, Any]) -> None:
        pass

    def generate_signal(self) -> dict[str, Any]:
        return {"action": "BUY"}

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        return None


@pytest.fixture
def registry() -> StrategyRegistry:
    return StrategyRegistry()


class TestRegister:
    """Test register method."""

    def test_register_valid_strategy(self, registry: StrategyRegistry) -> None:
        registry.register("fake_a", FakeStrategyA)
        assert "fake_a" in registry.list_strategies()

    def test_register_rejects_non_subclass(self, registry: StrategyRegistry) -> None:
        with pytest.raises(TypeError):
            registry.register("invalid", str)  # type: ignore[arg-type]

    def test_register_rejects_non_class(self, registry: StrategyRegistry) -> None:
        with pytest.raises(TypeError):
            registry.register("invalid", "not_a_class")  # type: ignore[arg-type]

    def test_register_overwrites_existing(self, registry: StrategyRegistry) -> None:
        registry.register("strat", FakeStrategyA)
        registry.register("strat", FakeStrategyB)
        assert registry.get("strat") is FakeStrategyB


class TestGet:
    """Test get method."""

    def test_get_returns_registered_class(self, registry: StrategyRegistry) -> None:
        registry.register("fake_a", FakeStrategyA)
        cls = registry.get("fake_a")
        assert cls is FakeStrategyA

    def test_get_raises_on_missing(self, registry: StrategyRegistry) -> None:
        with pytest.raises(KeyError, match="not_registered"):
            registry.get("not_registered")

    def test_returned_class_is_instantiable(self, registry: StrategyRegistry) -> None:
        registry.register("fake_a", FakeStrategyA)
        cls = registry.get("fake_a")
        instance = cls(config={"param": 1})
        assert isinstance(instance, BaseStrategy)
        assert instance.config["param"] == 1


class TestListStrategies:
    """Test list_strategies method."""

    def test_empty_registry(self, registry: StrategyRegistry) -> None:
        assert registry.list_strategies() == []

    def test_lists_all_registered(self, registry: StrategyRegistry) -> None:
        registry.register("fake_a", FakeStrategyA)
        registry.register("fake_b", FakeStrategyB)
        names = registry.list_strategies()
        assert "fake_a" in names
        assert "fake_b" in names
        assert len(names) == 2
