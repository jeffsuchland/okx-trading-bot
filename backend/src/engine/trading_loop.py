"""Main async trading loop that ties strategy, orders, and market data together."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.engine.pnl_tracker import PnlTracker
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
        trading_pair: str = "BTC-USDT",
        spend_per_trade: float = 10.0,
        pnl_tracker: PnlTracker | None = None,
    ) -> None:
        self._strategy = strategy
        self._order_manager = order_manager
        self._queue = market_data_queue
        self._tick_interval = tick_interval_seconds
        self._trading_pair = trading_pair
        self._spend_per_trade = spend_per_trade
        self._pnl_tracker = pnl_tracker
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

    async def _execute_signal(self, signal: dict[str, Any]) -> None:
        """Place orders based on the signal and record the trade."""
        action = signal.get("action", "HOLD")

        if action == "BUY":
            price = signal.get("price", 0.0)
            if price <= 0:
                logger.warning("BUY signal has no valid price, skipping order")
                return
            qty = str(round(self._spend_per_trade / float(price), 8))
            try:
                result = await self._order_manager.place_market_order(
                    symbol=self._trading_pair,
                    side="buy",
                    qty=qty,
                )
                logger.info("BUY order placed: %s", result)
                if self._pnl_tracker is not None:
                    self._pnl_tracker.record_trade({
                        "symbol": self._trading_pair,
                        "side": "buy",
                        "qty": qty,
                        "price": price,
                        "fee": 0.0,
                        "pnl": 0.0,
                    })
            except Exception as e:
                logger.error("Failed to place BUY order: %s", e)

        elif action == "SELL":
            price = signal.get("price", 0.0)
            if price <= 0:
                logger.warning("SELL signal has no valid price, skipping order")
                return
            qty = str(round(self._spend_per_trade / float(price), 8))
            try:
                result = await self._order_manager.place_market_order(
                    symbol=self._trading_pair,
                    side="sell",
                    qty=qty,
                )
                logger.info("SELL order placed: %s", result)
                if self._pnl_tracker is not None:
                    self._pnl_tracker.record_trade({
                        "symbol": self._trading_pair,
                        "side": "sell",
                        "qty": qty,
                        "price": price,
                        "fee": 0.0,
                        "pnl": 0.0,
                    })
            except Exception as e:
                logger.error("Failed to place SELL order: %s", e)

        elif action == "GRID":
            orders = signal.get("orders", [])
            for order in orders:
                side = order.get("side", "buy")
                price = float(order.get("price", 0))
                qty = str(order.get("qty", 0))
                if price <= 0 or float(qty) <= 0:
                    continue
                try:
                    result = await self._order_manager.place_limit_order(
                        symbol=self._trading_pair,
                        side=side,
                        qty=qty,
                        price=str(price),
                    )
                    logger.info("GRID limit order placed: %s %s @ %s", side, qty, price)
                    if self._pnl_tracker is not None:
                        self._pnl_tracker.record_trade({
                            "symbol": self._trading_pair,
                            "side": side,
                            "qty": qty,
                            "price": price,
                            "fee": 0.0,
                            "pnl": 0.0,
                        })
                except Exception as e:
                    logger.error("Failed to place GRID order %s @ %s: %s", side, price, e)

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
            try:
                self._strategy.analyze(data)
            except Exception:
                logger.exception("Error analyzing market data")

        if self._paused:
            return

        try:
            # Generate and execute signal
            signal = self._strategy.generate_signal()
            action = signal.get("action", "HOLD")

            if action != "HOLD":
                result = self._strategy.execute(signal)
                if result is not None:
                    logger.info("Signal executed: %s", action)
                    await self._execute_signal(signal)
        except Exception:
            logger.exception("Error generating or executing signal")

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
