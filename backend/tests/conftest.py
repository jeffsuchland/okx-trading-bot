"""Shared pytest fixtures for the OKX Trading Bot test suite."""

from __future__ import annotations

import random
from typing import Any
from unittest.mock import MagicMock

import pytest


class MockOkxClient:
    """Deterministic mock for the OKX API client.

    Returns configurable fake balances, tickers, and order responses.
    """

    def __init__(
        self,
        balances: list[dict[str, Any]] | None = None,
        ticker: dict[str, Any] | None = None,
        order_response: dict[str, Any] | None = None,
    ) -> None:
        self._balances = balances or [
            {"ccy": "USDT", "availBal": "1000.00", "eq": "1500.00"},
            {"ccy": "BTC", "availBal": "0.05", "eq": "0.05"},
        ]
        self._ticker = ticker or {
            "instId": "BTC-USDT",
            "last": "42000.00",
            "askPx": "42001.00",
            "bidPx": "41999.00",
            "vol24h": "1234.56",
        }
        self._order_response = order_response or {
            "ordId": "mock-order-001",
            "clOrdId": "",
            "sCode": "0",
            "sMsg": "",
        }

    def get_balances(self) -> list[dict[str, Any]]:
        return self._balances

    def get_ticker(self, inst_id: str = "BTC-USDT") -> dict[str, Any]:
        return {**self._ticker, "instId": inst_id}

    def place_order(
        self,
        inst_id: str,
        side: str,
        order_type: str,
        size: str,
        price: str | None = None,
    ) -> dict[str, Any]:
        return self._order_response

    def cancel_order(self, inst_id: str, ord_id: str) -> dict[str, Any]:
        return {"ordId": ord_id, "sCode": "0", "sMsg": ""}

    def get_positions(self) -> list[dict[str, Any]]:
        return []


@pytest.fixture
def mock_okx_client() -> MockOkxClient:
    """Provide a MockOkxClient with default responses."""
    return MockOkxClient()


@pytest.fixture
def mock_okx_client_factory():
    """Factory fixture to create MockOkxClient with custom responses."""
    def _factory(**kwargs: Any) -> MockOkxClient:
        return MockOkxClient(**kwargs)
    return _factory


@pytest.fixture
def sample_market_data() -> list[dict[str, Any]]:
    """Provide 100 candles of realistic OHLCV data for BTC-USDT.

    Simulates a random walk starting at $40,000 with ~1% volatility per candle.
    Uses a fixed seed for determinism.
    """
    rng = random.Random(42)
    candles: list[dict[str, Any]] = []
    price = 40000.0
    ts = 1700000000000  # epoch ms

    for i in range(100):
        change_pct = rng.gauss(0, 0.01)
        open_price = price
        close_price = open_price * (1 + change_pct)
        high_price = max(open_price, close_price) * (1 + abs(rng.gauss(0, 0.003)))
        low_price = min(open_price, close_price) * (1 - abs(rng.gauss(0, 0.003)))
        volume = rng.uniform(50, 500)

        candles.append({
            "ts": str(ts + i * 60000),
            "o": f"{open_price:.2f}",
            "h": f"{high_price:.2f}",
            "l": f"{low_price:.2f}",
            "c": f"{close_price:.2f}",
            "vol": f"{volume:.4f}",
        })
        price = close_price

    return candles


@pytest.fixture
def sample_prices(sample_market_data: list[dict[str, Any]]) -> list[float]:
    """Extract closing prices from sample market data as floats."""
    return [float(c["c"]) for c in sample_market_data]
