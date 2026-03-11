"""Tests for BaseStrategy abstract class."""

from __future__ import annotations

from typing import Any

import pytest

from src.strategies.base_strategy import BaseStrategy


class ConcreteStrategy(BaseStrategy):
    """Minimal concrete implementation for testing."""

    def analyze(self, market_data: dict[str, Any]) -> None:
        self._last_data = market_data

    def generate_signal(self) -> dict[str, Any]:
        return {"action": "HOLD"}

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        return {"executed": True, "signal": signal}


class TestBaseStrategyAbstract:
    """Test that BaseStrategy cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseStrategy()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        strategy = ConcreteStrategy()
        assert isinstance(strategy, BaseStrategy)


class TestBaseStrategyConfig:
    """Test config handling."""

    def test_default_config_is_empty_dict(self) -> None:
        strategy = ConcreteStrategy()
        assert strategy.config == {}

    def test_accepts_config_dict(self) -> None:
        config = {"rsi_period": 14, "overbought": 70}
        strategy = ConcreteStrategy(config=config)
        assert strategy.config["rsi_period"] == 14
        assert strategy.config["overbought"] == 70

    def test_get_config_returns_copy(self) -> None:
        config = {"rsi_period": 14}
        strategy = ConcreteStrategy(config=config)
        returned = strategy.get_config()
        returned["rsi_period"] = 99
        assert strategy.config["rsi_period"] == 14

    def test_update_config_merges(self) -> None:
        strategy = ConcreteStrategy(config={"rsi_period": 14})
        strategy.update_config({"overbought": 70})
        assert strategy.config["rsi_period"] == 14
        assert strategy.config["overbought"] == 70

    def test_update_config_overwrites(self) -> None:
        strategy = ConcreteStrategy(config={"rsi_period": 14})
        strategy.update_config({"rsi_period": 21})
        assert strategy.config["rsi_period"] == 21


class TestBaseStrategyMethods:
    """Test that abstract methods work on concrete subclass."""

    def test_analyze_stores_data(self) -> None:
        strategy = ConcreteStrategy()
        strategy.analyze({"last": 42000})
        assert strategy._last_data == {"last": 42000}

    def test_generate_signal_returns_dict(self) -> None:
        strategy = ConcreteStrategy()
        signal = strategy.generate_signal()
        assert signal["action"] == "HOLD"

    def test_execute_returns_result(self) -> None:
        strategy = ConcreteStrategy()
        result = strategy.execute({"action": "BUY"})
        assert result is not None
        assert result["executed"] is True
