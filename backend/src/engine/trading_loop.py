"""Main async trading loop that ties strategy, orders, and market data together."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.exchange.order_manager import OrderManager
from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class TradingLoop:
    """Async trading loop consuming market data and executing strategy signals."""

    def __init__(
        self,
        strategy: BaseStrategy,
        order_manager: OrderManager,
        market_data_queue: asyncio.Queue[dict[str, Any]],
        tick_interval_seconds: float = 5.0,
    ) -> None:
        self._strategy = strategy
        self._order_manager = order_manager
        self._queue = market_data_queue
        self._tick_interval = tick_interval_seconds
        self._running = False
        self._paused = False
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def status(self) -> str:
        if not self._running:
            return "stopped"
        if self._paused:
            return "paused"
        return "running"

    async def _tick(self) -> None:
        """Execute one tick: drain queue, analyze, generate signal, execute."""
        # Drain all available market data from the queue
        data_items: list[dict[str, Any]] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                data_items.append(item)
            except asyncio.QueueEmpty:
                break

        # Feed each data item to the strategy
        for data in data_items:
            self._strategy.analyze(data)

        if self._paused:
            return

        # Generate and execute signal
        signal = self._strategy.generate_signal()
        action = signal.get("action", "HOLD")

        if action != "HOLD":
            result = self._strategy.execute(signal)
            if result is not None:
                logger.info("Signal executed: %s", action)

    async def _loop(self) -> None:
        """Main loop running ticks at the configured interval."""
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Error during trading tick (continuing)")
            await asyncio.sleep(self._tick_interval)

    def start(self) -> asyncio.Task[None]:
        """Start the trading loop."""
        self._running = True
        self._paused = False
        self._task = asyncio.create_task(self._loop())
        logger.info("Trading loop started (interval=%.1fs)", self._tick_interval)
        return self._task

    async def stop(self) -> None:
        """Gracefully stop the trading loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Trading loop stopped")

    def pause(self) -> None:
        """Pause signal execution without stopping data consumption."""
        self._paused = True
        logger.info("Trading loop paused")

    def resume(self) -> None:
        """Resume signal execution."""
        self._paused = False
        logger.info("Trading loop resumed")
