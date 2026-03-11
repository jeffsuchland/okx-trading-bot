"""Tests for OKX API client wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from src.exchange.exceptions import OkxApiError
from src.exchange.okx_client import OkxClient


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock environment variables for OKX credentials."""
    monkeypatch.setenv("OKX_API_KEY", "test-api-key")
    monkeypatch.setenv("OKX_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("OKX_PASSPHRASE", "test-passphrase")
    monkeypatch.setenv("OKX_SIMULATED", "true")


@pytest.fixture
def client(mock_env: None) -> OkxClient:
    """Create an OkxClient with mocked SDK internals."""
    with patch("src.exchange.okx_client.Account.AccountAPI") as mock_account, \
         patch("src.exchange.okx_client.MarketData.MarketAPI") as mock_market, \
         patch("src.exchange.okx_client.Trade.TradeAPI") as mock_trade:
        c = OkxClient()
        c._account_api = mock_account.return_value
        c._market_api = mock_market.return_value
        c._trade_api = mock_trade.return_value
        return c


class TestOkxClientCredentials:
    """Test credential loading from environment."""

    def test_loads_credentials_from_env(self, mock_env: None) -> None:
        with patch("src.exchange.okx_client.Account.AccountAPI"), \
             patch("src.exchange.okx_client.MarketData.MarketAPI"), \
             patch("src.exchange.okx_client.Trade.TradeAPI"):
            c = OkxClient()
            assert c.api_key == "test-api-key"
            assert c.secret_key == "test-secret-key"
            assert c.passphrase == "test-passphrase"

    def test_accepts_explicit_credentials(self) -> None:
        with patch("src.exchange.okx_client.Account.AccountAPI"), \
             patch("src.exchange.okx_client.MarketData.MarketAPI"), \
             patch("src.exchange.okx_client.Trade.TradeAPI"):
            c = OkxClient(api_key="ak", secret_key="sk", passphrase="pp")
            assert c.api_key == "ak"
            assert c.secret_key == "sk"
            assert c.passphrase == "pp"


class TestGetAccountBalance:
    """Test get_account_balance method."""

    def test_returns_parsed_usdt_balance(self, client: OkxClient) -> None:
        client._account_api.get_account_balance.return_value = {
            "code": "0",
            "data": [
                {
                    "details": [
                        {
                            "ccy": "USDT",
                            "availBal": "1000.50",
                            "eq": "1200.75",
                            "frozenBal": "200.25",
                        }
                    ]
                }
            ],
        }
        result = client.get_account_balance("USDT")
        assert result["currency"] == "USDT"
        assert result["available"] == 1000.50
        assert result["equity"] == 1200.75
        assert result["frozen"] == 200.25

    def test_returns_zeros_when_currency_not_found(self, client: OkxClient) -> None:
        client._account_api.get_account_balance.return_value = {
            "code": "0",
            "data": [{"details": [{"ccy": "BTC", "availBal": "1.0", "eq": "1.0", "frozenBal": "0"}]}],
        }
        result = client.get_account_balance("USDT")
        assert result["available"] == 0.0

    def test_raises_on_api_error(self, client: OkxClient) -> None:
        client._account_api.get_account_balance.return_value = {
            "code": "50013",
            "msg": "Invalid API key",
        }
        with pytest.raises(OkxApiError) as exc_info:
            client.get_account_balance()
        assert exc_info.value.code == "50013"
        assert "Invalid API key" in exc_info.value.message


class TestGetTicker:
    """Test get_ticker method."""

    def test_returns_parsed_ticker(self, client: OkxClient) -> None:
        client._market_api.get_ticker.return_value = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT",
                    "bidPx": "42000.5",
                    "askPx": "42001.0",
                    "last": "42000.8",
                    "vol24h": "15000",
                    "ts": "1710000000000",
                }
            ],
        }
        result = client.get_ticker("BTC-USDT")
        assert result["symbol"] == "BTC-USDT"
        assert result["bid"] == 42000.5
        assert result["ask"] == 42001.0
        assert result["last"] == 42000.8
        assert result["volume_24h"] == 15000.0
        assert result["timestamp"] == "1710000000000"

    def test_raises_on_api_error(self, client: OkxClient) -> None:
        client._market_api.get_ticker.return_value = {
            "code": "51001",
            "msg": "Instrument does not exist",
        }
        with pytest.raises(OkxApiError) as exc_info:
            client.get_ticker("FAKE-COIN")
        assert exc_info.value.code == "51001"


class TestPlaceOrder:
    """Test place_order method."""

    def test_places_limit_order_successfully(self, client: OkxClient) -> None:
        client._trade_api.place_order.return_value = {
            "code": "0",
            "data": [
                {
                    "ordId": "123456789",
                    "clOrdId": "client-order-1",
                    "sCode": "0",
                    "sMsg": "",
                }
            ],
        }
        result = client.place_order("BTC-USDT", "buy", "0.001", "42000")
        assert result["order_id"] == "123456789"
        assert result["client_order_id"] == "client-order-1"
        client._trade_api.place_order.assert_called_once_with(
            instId="BTC-USDT",
            tdMode="cash",
            side="buy",
            ordType="limit",
            sz="0.001",
            px="42000",
        )

    def test_places_market_order_without_price(self, client: OkxClient) -> None:
        client._trade_api.place_order.return_value = {
            "code": "0",
            "data": [{"ordId": "987654321", "clOrdId": "", "sCode": "0", "sMsg": ""}],
        }
        result = client.place_order("BTC-USDT", "sell", "0.001", order_type="market")
        assert result["order_id"] == "987654321"

    def test_raises_on_order_error(self, client: OkxClient) -> None:
        client._trade_api.place_order.return_value = {
            "code": "51008",
            "msg": "Insufficient balance",
        }
        with pytest.raises(OkxApiError) as exc_info:
            client.place_order("BTC-USDT", "buy", "100", "42000")
        assert exc_info.value.code == "51008"


class TestCancelOrder:
    """Test cancel_order method."""

    def test_cancels_order_successfully(self, client: OkxClient) -> None:
        client._trade_api.cancel_order.return_value = {
            "code": "0",
            "data": [{"ordId": "123456789", "sCode": "0", "sMsg": ""}],
        }
        result = client.cancel_order("BTC-USDT", "123456789")
        assert result["ordId"] == "123456789"


class TestHealthCheck:
    """Test health_check method."""

    def test_returns_true_when_api_reachable(self, client: OkxClient) -> None:
        client._market_api.get_system_time.return_value = {
            "code": "0",
            "data": [{"ts": "1710000000000"}],
        }
        assert client.health_check() is True

    def test_returns_false_when_api_unreachable(self, client: OkxClient) -> None:
        client._market_api.get_system_time.side_effect = ConnectionError("timeout")
        assert client.health_check() is False

    def test_returns_false_on_api_error(self, client: OkxClient) -> None:
        client._market_api.get_system_time.return_value = {
            "code": "50000",
            "msg": "Service unavailable",
        }
        assert client.health_check() is False
