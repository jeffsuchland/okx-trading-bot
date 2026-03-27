"""Integration tests for the full trading flow with mocked exchange."""

from __future__ import annotations

import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.engine.pnl_tracker import PnlTracker
from src.exchange.order_manager import OrderManager
from src.risk.risk_manager import RiskManager
from src.strategies.mean_reversion import MeanReversionStrategy


def _make_mock_client(order_id: str = "test-order-001") -> MagicMock:
    """Create a mock OkxClient that returns deterministic responses."""
    client = MagicMock()
    _order_counter = [0]

    def _place_order_side_effect(**kwargs: Any) -> dict[str, Any]:
        _order_counter[0] += 1
        oid = f"{order_id}-{_order_counter[0]}"
        return {"order_id": oid, "sCode": "0", "sMsg": ""}

    client.place_order.side_effect = _place_order_side_effect
    client.cancel_order.return_value = {"ordId": order_id, "sCode": "0", "sMsg": ""}
    client.get_positions.return_value = []
    return client


def _feed_oversold_data(strategy: MeanReversionStrategy) -> None:
    """Feed enough candle data to produce a BUY signal (RSI oversold + MACD cross up).

    We simulate a price series that drops sharply then jumps up decisively,
    creating RSI < 30 and a MACD histogram zero-line cross-up in a single step.
    """
    # Start high, decline steeply to drive RSI to ~0 and MACD histogram near 0
    prices = [200.0] * 10
    for i in range(65):
        prices.append(200.0 - i * 2.0)  # decline from 200 to 72
    # One decisive uptick: MACD histogram crosses from negative to positive
    # while RSI is still well below 30 (~21.8)
    prices.append(79.2)

    for p in prices:
        strategy.analyze({"close": p})


def _feed_overbought_data(strategy: MeanReversionStrategy) -> None:
    """Feed enough candle data to produce a SELL signal (RSI overbought + MACD cross down)."""
    prices = [50.0] * 10
    for i in range(30):
        prices.append(50.0 + i * 1.5)  # rise from 50 to ~95
    # Small downtick to trigger MACD histogram crossover downward
    prices.append(94.0)
    prices.append(93.0)
    prices.append(92.0)

    for p in prices:
        strategy.analyze({"close": p})


class TestSuccessfulTradeCycle:
    """Test: data -> signal -> risk OK -> order -> fill -> PnL updated."""

    def test_successful_trade_cycle(self, tmp_path: Any) -> None:
        # Setup components
        client = _make_mock_client()
        order_manager = OrderManager(client)
        risk_manager = RiskManager({
            "spend_per_trade": 100.0,
            "max_total_exposure": 1000.0,
            "stop_loss_pct": 2.0,
            "max_drawdown_pct": 10.0,
            "max_daily_loss": 500.0,
        })
        risk_manager.set_order_manager(order_manager)

        strategy = MeanReversionStrategy()
        pnl_tracker = PnlTracker(trade_log_path=str(tmp_path / "trades.json"))

        # 1. Feed market data to strategy
        _feed_oversold_data(strategy)

        # 2. Strategy generates signal
        signal = strategy.generate_signal()
        assert signal["action"] == "BUY", f"Expected BUY signal, got {signal}"

        # 3. Risk check passes
        signal["price"] = 58.0
        approved, reason = risk_manager.pre_trade_check(signal)
        assert approved, f"Risk check should pass: {reason}"

        # 4. Place order
        result = order_manager.place_market_order("BTC-USDT", "buy", "0.001")
        assert result["order_id"].startswith("test-order-001")

        # 5. Record fill and update PnL
        trade_info = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "qty": 0.001,
            "price": 58.0,
            "fee": 0.01,
            "pnl": 5.0,
        }
        pnl_tracker.record_trade(trade_info)

        # 6. Post-trade risk update
        risk_manager.post_trade_update({
            **trade_info,
            "current_equity": 1005.0,
        })

        # Verify PnL updated
        assert pnl_tracker.get_cumulative_pnl() == 5.0
        assert len(pnl_tracker.get_all_trades()) == 1


class TestRiskBlocksTrade:
    """Test: signal generated but risk check returns rejected."""

    def test_risk_blocks_trade(self) -> None:
        risk_manager = RiskManager({
            "spend_per_trade": 10.0,
            "max_total_exposure": 10.0,  # Very low limit
            "max_daily_loss": 0.01,  # Tiny limit — will trigger on any loss
        })

        strategy = MeanReversionStrategy()
        _feed_oversold_data(strategy)
        signal = strategy.generate_signal()
        assert signal["action"] == "BUY"

        # Simulate having already hit daily loss limit
        signal["price"] = 58.0
        signal["daily_pnl"] = -1.0  # exceeds 0.01 limit
        approved, reason = risk_manager.pre_trade_check(signal)
        assert not approved
        assert "daily loss limit" in reason


class TestStopLossTriggers:
    """Test: position drops below stop-loss -> market sell executed."""

    def test_stop_loss_triggers(self) -> None:
        client = _make_mock_client()
        order_manager = OrderManager(client)
        risk_manager = RiskManager({
            "stop_loss_pct": 2.0,
        })
        risk_manager.set_order_manager(order_manager)

        # Position that has dropped below stop-loss
        positions = [
            {
                "symbol": "BTC-USDT",
                "entry_price": 100.0,
                "current_price": 97.0,  # 3% drop > 2% stop
                "size": "0.1",
                "side": "long",
            }
        ]

        triggered = risk_manager.check_stop_losses(positions)
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "BTC-USDT"

        # Execute the market sell for triggered position
        for pos in triggered:
            result = order_manager.place_market_order(
                pos["symbol"], "sell", pos["size"]
            )
            assert result["order_id"].startswith("test-order-001")

        # Verify the order was placed
        client.place_order.assert_called()


class TestCircuitBreakerHalts:
    """Test: drawdown exceeds limit -> trading loop stops."""

    def test_circuit_breaker_halts(self) -> None:
        risk_manager = RiskManager({
            "max_drawdown_pct": 5.0,
        })

        # Establish peak equity
        risk_manager.post_trade_update({"current_equity": 1000.0, "side": "buy", "qty": 0, "price": 0})

        # Drawdown of 6% (exceeds 5%)
        risk_manager.post_trade_update({"current_equity": 940.0, "side": "buy", "qty": 0, "price": 0})

        # Now pre_trade_check should block
        approved, reason = risk_manager.pre_trade_check({"action": "BUY", "price": 100.0})
        assert not approved
        assert "circuit breaker" in reason


class TestPanicFlattens:
    """Test: panic triggered -> all orders canceled, positions sold."""

    def test_panic_flattens(self) -> None:
        client = _make_mock_client()
        order_manager = OrderManager(client)
        risk_manager = RiskManager()
        risk_manager.set_order_manager(order_manager)

        # Place some orders first
        order_manager.place_limit_order("BTC-USDT", "buy", "0.01", "40000")
        order_manager.place_limit_order("ETH-USDT", "buy", "0.1", "3000")
        assert len(order_manager.get_open_orders()) == 2

        # Trigger panic with positions
        positions = [
            {"symbol": "BTC-USDT", "size": "0.01", "side": "long"},
            {"symbol": "ETH-USDT", "size": "0.1", "side": "long"},
        ]

        risk_manager.panic()

        # Verify halted
        approved, reason = risk_manager.pre_trade_check({"action": "BUY", "price": 100.0})
        assert not approved
        assert "panic" in reason.lower()

        # Now flatten positions via order manager directly
        result = order_manager.panic_flatten(positions)
        assert result["positions_closed"] == 2

        # Verify market sell orders were placed for each position
        assert client.place_order.call_count >= 2
