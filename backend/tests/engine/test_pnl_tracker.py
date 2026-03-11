"""Tests for Trade history and PnL tracker."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import pytest

from src.engine.pnl_tracker import PnlTracker


@pytest.fixture
def tmp_log_path(tmp_path: Any) -> str:
    """Create a temp path for the trade log."""
    return str(tmp_path / "trade_log.json")


@pytest.fixture
def tracker(tmp_log_path: str) -> PnlTracker:
    """Create a PnlTracker with a temp file."""
    return PnlTracker(trade_log_path=tmp_log_path)


def _make_trade(symbol: str = "BTC-USDT", side: str = "buy", qty: float = 0.001,
                price: float = 42000.0, fee: float = 0.01, pnl: float = 0.0,
                timestamp: str | None = None) -> dict[str, Any]:
    """Helper to create a trade dict."""
    t: dict[str, Any] = {
        "symbol": symbol, "side": side, "qty": qty,
        "price": price, "fee": fee, "pnl": pnl,
    }
    if timestamp:
        t["timestamp"] = timestamp
    return t


class TestRecordTrade:
    """Test record_trade method."""

    def test_stores_trade_with_all_fields(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade())
        trades = tracker.get_all_trades()
        assert len(trades) == 1
        t = trades[0]
        assert t["symbol"] == "BTC-USDT"
        assert t["side"] == "buy"
        assert t["qty"] == 0.001
        assert t["price"] == 42000.0
        assert t["fee"] == 0.01
        assert "timestamp" in t

    def test_auto_generates_timestamp(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade())
        ts = tracker.get_all_trades()[0]["timestamp"]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert ts.startswith(today)

    def test_records_multiple_trades(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=5.0))
        tracker.record_trade(_make_trade(pnl=-2.0))
        tracker.record_trade(_make_trade(pnl=3.0))
        assert len(tracker.get_all_trades()) == 3


class TestGetDailyPnl:
    """Test get_daily_pnl method."""

    def test_returns_pnl_for_today(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=10.0))
        tracker.record_trade(_make_trade(pnl=-3.0))
        assert tracker.get_daily_pnl() == 7.0

    def test_excludes_other_days(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=10.0))  # today
        tracker.record_trade(_make_trade(pnl=100.0, timestamp="2020-01-01T00:00:00+00:00"))
        assert tracker.get_daily_pnl() == 10.0

    def test_returns_zero_with_no_trades(self, tracker: PnlTracker) -> None:
        assert tracker.get_daily_pnl() == 0.0


class TestGetCumulativePnl:
    """Test get_cumulative_pnl method."""

    def test_returns_total_pnl(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=10.0))
        tracker.record_trade(_make_trade(pnl=-3.0))
        tracker.record_trade(_make_trade(pnl=5.0))
        assert tracker.get_cumulative_pnl() == 12.0

    def test_returns_zero_with_no_trades(self, tracker: PnlTracker) -> None:
        assert tracker.get_cumulative_pnl() == 0.0


class TestGetWinLossRatio:
    """Test get_win_loss_ratio method."""

    def test_returns_correct_counts(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=10.0))
        tracker.record_trade(_make_trade(pnl=-3.0))
        tracker.record_trade(_make_trade(pnl=5.0))
        result = tracker.get_win_loss_ratio()
        assert result["wins"] == 2
        assert result["losses"] == 1
        assert result["total"] == 3
        assert result["win_rate"] == pytest.approx(66.67)

    def test_zero_trades(self, tracker: PnlTracker) -> None:
        result = tracker.get_win_loss_ratio()
        assert result["wins"] == 0
        assert result["losses"] == 0
        assert result["win_rate"] == 0.0

    def test_all_wins(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=1.0))
        tracker.record_trade(_make_trade(pnl=2.0))
        assert tracker.get_win_loss_ratio()["win_rate"] == 100.0

    def test_all_losses(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=-1.0))
        tracker.record_trade(_make_trade(pnl=-2.0))
        assert tracker.get_win_loss_ratio()["win_rate"] == 0.0


class TestGetRecentTrades:
    """Test get_recent_trades method."""

    def test_returns_last_n_trades(self, tracker: PnlTracker) -> None:
        for i in range(20):
            tracker.record_trade(_make_trade(pnl=float(i)))
        recent = tracker.get_recent_trades(5)
        assert len(recent) == 5
        assert recent[-1]["pnl"] == 19.0
        assert recent[0]["pnl"] == 15.0

    def test_returns_all_if_fewer_than_n(self, tracker: PnlTracker) -> None:
        tracker.record_trade(_make_trade(pnl=1.0))
        tracker.record_trade(_make_trade(pnl=2.0))
        recent = tracker.get_recent_trades(10)
        assert len(recent) == 2

    def test_default_n_is_10(self, tracker: PnlTracker) -> None:
        for i in range(15):
            tracker.record_trade(_make_trade(pnl=float(i)))
        assert len(tracker.get_recent_trades()) == 10


class TestPersistence:
    """Test trade log persistence to JSON file."""

    def test_saves_to_file(self, tracker: PnlTracker, tmp_log_path: str) -> None:
        tracker.record_trade(_make_trade(pnl=5.0))
        assert os.path.exists(tmp_log_path)
        with open(tmp_log_path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_loads_on_startup(self, tmp_log_path: str) -> None:
        # Write some trades to the file first
        trades = [{"timestamp": "2026-03-10T00:00:00+00:00", "symbol": "BTC-USDT",
                    "side": "buy", "qty": 0.001, "price": 42000.0, "fee": 0.01, "pnl": 5.0}]
        os.makedirs(os.path.dirname(tmp_log_path) or ".", exist_ok=True)
        with open(tmp_log_path, "w") as f:
            json.dump(trades, f)

        # Create new tracker — should load existing trades
        tracker2 = PnlTracker(trade_log_path=tmp_log_path)
        assert len(tracker2.get_all_trades()) == 1
        assert tracker2.get_cumulative_pnl() == 5.0

    def test_survives_missing_file(self, tmp_path: Any) -> None:
        path = str(tmp_path / "nonexistent" / "trade_log.json")
        tracker = PnlTracker(trade_log_path=path)
        assert len(tracker.get_all_trades()) == 0

    def test_creates_directory_on_save(self, tmp_path: Any) -> None:
        path = str(tmp_path / "newdir" / "trade_log.json")
        tracker = PnlTracker(trade_log_path=path)
        tracker.record_trade(_make_trade(pnl=1.0))
        assert os.path.exists(path)
