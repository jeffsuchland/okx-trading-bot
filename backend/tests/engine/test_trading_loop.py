"""Tests for Trading engine main loop."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.engine.trading_loop import TradingLoop
from src.strategies.base_strategy import BaseStrategy


class FakeStrategy(BaseStrategy):
    """Minimal strategy for testing the loop."""

    def __init__(self) -> None:
        super().__init__()
        self.analyzed: list[dict[str, Any]] = []
        self.signal_to_return: dict[str, Any] = {"action": "HOLD"}

    def analyze(self, market_data: dict[str, Any]) -> None:
        self.analyzed.append(market_data)

    def generate_signal(self) -> dict[str, Any]:
        return self.signal_to_return

    def execute(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("action") == "HOLD":
            return None
        return signal


@pytest.fixture
def fake_strategy() -> FakeStrategy:
    return FakeStrategy()


@pytest.fixture
def mock_order_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def queue() -> asyncio.Queue:
    return asyncio.Queue()


@pytest.fixture
def loop(fake_strategy: FakeStrategy, mock_order_manager: MagicMock, queue: asyncio.Queue) -> TradingLoop:
    return TradingLoop(
        strategy=fake_strategy,
        order_manager=mock_order_manager,
        market_data_queue=queue,
        tick_interval_seconds=0.01,
    )


class TestConstructor:
    """Test TradingLoop accepts required components."""

    def test_accepts_strategy_and_order_manager(
        self, fake_strategy: FakeStrategy, mock_order_manager: MagicMock, queue: asyncio.Queue
    ) -> None:
        tl = TradingLoop(
            strategy=fake_strategy,
            order_manager=mock_order_manager,
            market_data_queue=queue,
        )
        assert tl._strategy is fake_strategy
        assert tl._order_manager is mock_order_manager

    def test_default_tick_interval(
        self, fake_strategy: FakeStrategy, mock_order_manager: MagicMock, queue: asyncio.Queue
    ) -> None:
        tl = TradingLoop(
            strategy=fake_strategy,
            order_manager=mock_order_manager,
            market_data_queue=queue,
        )
        assert tl._tick_interval == 5.0

    def test_custom_tick_interval(self, loop: TradingLoop) -> None:
        assert loop._tick_interval == 0.01


class TestStartStop:
    """Test start and stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, loop: TradingLoop) -> None:
        task = loop.start()
        assert loop.is_running is True
        assert loop.status == "running"
        await loop.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, loop: TradingLoop) -> None:
        loop.start()
        await loop.stop()
        assert loop.is_running is False
        assert loop.status == "stopped"


class TestPauseResume:
    """Test pause and resume toggle."""

    @pytest.mark.asyncio
    async def test_pause_sets_paused(self, loop: TradingLoop) -> None:
        loop.start()
        loop.pause()
        assert loop.is_paused is True
        assert loop.status == "paused"
        await loop.stop()

    @pytest.mark.asyncio
    async def test_resume_clears_paused(self, loop: TradingLoop) -> None:
        loop.start()
        loop.pause()
        loop.resume()
        assert loop.is_paused is False
        assert loop.status == "running"
        await loop.stop()


class TestTickExecution:
    """Test that each tick calls strategy methods in order."""

    @pytest.mark.asyncio
    async def test_tick_analyzes_queue_data(
        self, loop: TradingLoop, queue: asyncio.Queue, fake_strategy: FakeStrategy
    ) -> None:
        await queue.put({"last": 42000})
        await queue.put({"last": 42100})
        await loop._tick()
        assert len(fake_strategy.analyzed) == 2

    @pytest.mark.asyncio
    async def test_tick_generates_signal(
        self, loop: TradingLoop, fake_strategy: FakeStrategy
    ) -> None:
        fake_strategy.signal_to_return = {"action": "BUY", "reason": "test"}
        await loop._tick()
        # No error, signal was processed

    @pytest.mark.asyncio
    async def test_tick_paused_skips_signal(
        self, loop: TradingLoop, queue: asyncio.Queue, fake_strategy: FakeStrategy
    ) -> None:
        fake_strategy.signal_to_return = {"action": "BUY", "reason": "test"}
        await queue.put({"last": 42000})
        loop._paused = True
        await loop._tick()
        # Data was still analyzed even though paused
        assert len(fake_strategy.analyzed) == 1


class TestErrorHandling:
    """Test that errors in a tick don't crash the loop."""

    @pytest.mark.asyncio
    async def test_error_in_tick_is_caught(self, loop: TradingLoop, fake_strategy: FakeStrategy) -> None:
        # Make generate_signal raise an error
        def bad_signal() -> dict[str, Any]:
            raise ValueError("strategy error")

        fake_strategy.generate_signal = bad_signal  # type: ignore[assignment]

        # _tick should not raise
        await loop._tick()

    @pytest.mark.asyncio
    async def test_loop_continues_after_error(self, loop: TradingLoop, fake_strategy: FakeStrategy) -> None:
        call_count = 0
        original_signal = fake_strategy.generate_signal

        def sometimes_bad() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first tick error")
            return original_signal()

        fake_strategy.generate_signal = sometimes_bad  # type: ignore[assignment]

        loop.start()
        await asyncio.sleep(0.05)  # Let a few ticks run
        await loop.stop()
        # Should have run more than 1 tick despite the first error
        assert call_count > 1


class TestConfigurable:
    """Test configurable tick interval."""

    def test_tick_interval_configurable(
        self, fake_strategy: FakeStrategy, mock_order_manager: MagicMock, queue: asyncio.Queue
    ) -> None:
        tl = TradingLoop(
            strategy=fake_strategy,
            order_manager=mock_order_manager,
            market_data_queue=queue,
            tick_interval_seconds=10.0,
        )
        assert tl._tick_interval == 10.0
