"""Tests to verify shared conftest fixtures work correctly."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import MockOkxClient


class TestMockOkxClient:
    """Verify MockOkxClient fixture returns deterministic responses."""

    def test_default_balances(self, mock_okx_client: MockOkxClient) -> None:
        balances = mock_okx_client.get_balances()
        assert len(balances) == 2
        assert balances[0]["ccy"] == "USDT"
        assert balances[0]["availBal"] == "1000.00"

    def test_default_ticker(self, mock_okx_client: MockOkxClient) -> None:
        ticker = mock_okx_client.get_ticker()
        assert ticker["instId"] == "BTC-USDT"
        assert ticker["last"] == "42000.00"

    def test_ticker_with_custom_inst_id(self, mock_okx_client: MockOkxClient) -> None:
        ticker = mock_okx_client.get_ticker("ETH-USDT")
        assert ticker["instId"] == "ETH-USDT"

    def test_place_order(self, mock_okx_client: MockOkxClient) -> None:
        result = mock_okx_client.place_order("BTC-USDT", "buy", "market", "0.001")
        assert result["ordId"] == "mock-order-001"
        assert result["sCode"] == "0"

    def test_cancel_order(self, mock_okx_client: MockOkxClient) -> None:
        result = mock_okx_client.cancel_order("BTC-USDT", "order-123")
        assert result["ordId"] == "order-123"

    def test_get_positions(self, mock_okx_client: MockOkxClient) -> None:
        assert mock_okx_client.get_positions() == []


class TestMockOkxClientFactory:
    """Verify factory fixture creates custom MockOkxClient."""

    def test_custom_balances(self, mock_okx_client_factory) -> None:
        custom_balances = [{"ccy": "ETH", "availBal": "10.0", "eq": "10.0"}]
        client = mock_okx_client_factory(balances=custom_balances)
        assert client.get_balances() == custom_balances

    def test_custom_ticker(self, mock_okx_client_factory) -> None:
        custom_ticker = {"instId": "ETH-USDT", "last": "3000.00", "askPx": "3001", "bidPx": "2999", "vol24h": "500"}
        client = mock_okx_client_factory(ticker=custom_ticker)
        assert client.get_ticker()["last"] == "3000.00"

    def test_custom_order_response(self, mock_okx_client_factory) -> None:
        custom_order = {"ordId": "custom-001", "clOrdId": "", "sCode": "0", "sMsg": ""}
        client = mock_okx_client_factory(order_response=custom_order)
        assert client.place_order("BTC-USDT", "buy", "limit", "0.01", "40000")["ordId"] == "custom-001"


class TestSampleMarketData:
    """Verify sample market data fixture provides 100 candles."""

    def test_has_100_candles(self, sample_market_data: list[dict[str, Any]]) -> None:
        assert len(sample_market_data) == 100

    def test_candle_has_ohlcv_fields(self, sample_market_data: list[dict[str, Any]]) -> None:
        candle = sample_market_data[0]
        assert "ts" in candle
        assert "o" in candle
        assert "h" in candle
        assert "l" in candle
        assert "c" in candle
        assert "vol" in candle

    def test_prices_are_numeric(self, sample_market_data: list[dict[str, Any]]) -> None:
        for candle in sample_market_data:
            assert float(candle["o"]) > 0
            assert float(candle["h"]) >= float(candle["l"])

    def test_deterministic(self, sample_market_data: list[dict[str, Any]]) -> None:
        # Same seed should produce same first candle
        assert sample_market_data[0]["o"] == "40000.00"


class TestSamplePrices:
    """Verify sample_prices fixture."""

    def test_has_100_prices(self, sample_prices: list[float]) -> None:
        assert len(sample_prices) == 100

    def test_all_positive(self, sample_prices: list[float]) -> None:
        assert all(p > 0 for p in sample_prices)
