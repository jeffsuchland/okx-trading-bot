"""Trade history recording and PnL metrics computation."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PnlTracker:
    """Records executed trades and computes running PnL metrics.

    Persists trade log to a JSON file for recovery across restarts.
    """

    def __init__(self, trade_log_path: str = "data/trade_log.json") -> None:
        self._trade_log_path = trade_log_path
        self._trades: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load existing trade log from disk."""
        if os.path.exists(self._trade_log_path):
            try:
                with open(self._trade_log_path, "r") as f:
                    self._trades = json.load(f)
                logger.info("Loaded %d trades from %s", len(self._trades), self._trade_log_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load trade log: %s", e)
                self._trades = []

    def _save(self) -> None:
        """Persist trade log to disk."""
        os.makedirs(os.path.dirname(self._trade_log_path) or ".", exist_ok=True)
        try:
            with open(self._trade_log_path, "w") as f:
                json.dump(self._trades, f, indent=2)
        except OSError as e:
            logger.error("Failed to save trade log: %s", e)

    def record_trade(self, trade_info: dict[str, Any]) -> None:
        """Record a trade with timestamp, symbol, side, qty, price, fee.

        Args:
            trade_info: Dict with keys: symbol, side, qty, price, fee, and optionally pnl.
        """
        trade = {
            "timestamp": trade_info.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "symbol": trade_info.get("symbol", ""),
            "side": trade_info.get("side", ""),
            "qty": float(trade_info.get("qty", 0)),
            "price": float(trade_info.get("price", 0)),
            "fee": float(trade_info.get("fee", 0)),
            "pnl": float(trade_info.get("pnl", 0)),
        }
        self._trades.append(trade)
        self._save()
        logger.info("Recorded trade: %s %s %s @ %s (pnl=%.4f)", trade["side"], trade["qty"], trade["symbol"], trade["price"], trade["pnl"])

    def get_daily_pnl(self) -> float:
        """Return PnL for the current UTC day."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = 0.0
        for trade in self._trades:
            ts = trade.get("timestamp", "")
            if ts.startswith(today):
                daily += float(trade.get("pnl", 0))
        return daily

    def get_cumulative_pnl(self) -> float:
        """Return total PnL since inception."""
        return sum(float(t.get("pnl", 0)) for t in self._trades)

    def get_win_loss_ratio(self) -> dict[str, Any]:
        """Return wins, losses, and win_rate percentage."""
        wins = sum(1 for t in self._trades if float(t.get("pnl", 0)) > 0)
        losses = sum(1 for t in self._trades if float(t.get("pnl", 0)) < 0)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0.0
        return {
            "wins": wins,
            "losses": losses,
            "total": total,
            "win_rate": round(win_rate, 2),
        }

    def get_recent_trades(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the last N trades."""
        return self._trades[-n:]

    def get_all_trades(self) -> list[dict[str, Any]]:
        """Return all recorded trades."""
        return list(self._trades)
