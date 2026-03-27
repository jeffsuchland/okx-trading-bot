"""Tests for Order management service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.exchange.order_manager import OrderManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mocked OkxClient."""
    client = MagicMock()
    client.place_order.return_value = {
        "order_id": "ord-001",
        "client_order_id": "",
        "status_code": "0",
        "status_msg": "",
    }
    client.cancel_order.return_value = {"ordId": "ord-001", "sCode": "0", "sMsg": ""}
    return client


@pytest.fixture
def manager(mock_client: MagicMock) -> OrderManager:
    """Create an OrderManager with mocked client and no rate limiting."""
    return OrderManager(client=mock_client, max_requests_per_window=1000, window_seconds=0.001)


class TestPlaceLimitOrder:
    """Test place_limit_order method."""

    async def test_places_order_and_tracks_it(self, manager: OrderManager, mock_client: MagicMock) -> None:
        result = await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        assert result["order_id"] == "ord-001"
        mock_client.place_order.assert_called_once_with(
            symbol="BTC-USDT",
            side="buy",
            size="0.001",
            price="42000",
            order_type="limit",
            trade_mode="cash",
        )
        open_orders = manager.get_open_orders()
        assert len(open_orders) == 1
        assert open_orders[0]["order_id"] == "ord-001"
        assert open_orders[0]["symbol"] == "BTC-USDT"
        assert open_orders[0]["side"] == "buy"

    async def test_tracks_multiple_orders(self, manager: OrderManager, mock_client: MagicMock) -> None:
        mock_client.place_order.side_effect = [
            {"order_id": "ord-001", "client_order_id": "", "status_code": "0", "status_msg": ""},
            {"order_id": "ord-002", "client_order_id": "", "status_code": "0", "status_msg": ""},
        ]
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        await manager.place_limit_order("ETH-USDT", "sell", "0.01", "3000")
        assert len(manager.get_open_orders()) == 2


class TestCancelOrder:
    """Test cancel_order method."""

    async def test_cancels_and_removes_from_tracking(self, manager: OrderManager, mock_client: MagicMock) -> None:
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        assert len(manager.get_open_orders()) == 1

        await manager.cancel_order("BTC-USDT", "ord-001")
        mock_client.cancel_order.assert_called_once_with(symbol="BTC-USDT", order_id="ord-001")
        assert len(manager.get_open_orders()) == 0

    async def test_cancel_nonexistent_order_does_not_crash(self, manager: OrderManager) -> None:
        await manager.cancel_order("BTC-USDT", "nonexistent")
        assert len(manager.get_open_orders()) == 0


class TestGetOpenOrders:
    """Test get_open_orders method."""

    def test_returns_empty_list_when_no_orders(self, manager: OrderManager) -> None:
        assert manager.get_open_orders() == []

    async def test_returns_list_of_tracked_orders(self, manager: OrderManager) -> None:
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        orders = manager.get_open_orders()
        assert len(orders) == 1
        assert orders[0]["status"] == "open"


class TestCancelAllOrders:
    """Test cancel_all_orders method."""

    async def test_cancels_all_tracked_orders(self, manager: OrderManager, mock_client: MagicMock) -> None:
        mock_client.place_order.side_effect = [
            {"order_id": "ord-001", "client_order_id": "", "status_code": "0", "status_msg": ""},
            {"order_id": "ord-002", "client_order_id": "", "status_code": "0", "status_msg": ""},
        ]
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        await manager.place_limit_order("ETH-USDT", "sell", "0.01", "3000")
        assert len(manager.get_open_orders()) == 2

        results = await manager.cancel_all_orders()
        assert len(results) == 2
        assert len(manager.get_open_orders()) == 0

    async def test_cancel_all_with_no_orders(self, manager: OrderManager) -> None:
        results = await manager.cancel_all_orders()
        assert results == []


class TestPanicFlatten:
    """Test panic_flatten method."""

    async def test_cancels_orders_and_sells_positions(self, manager: OrderManager, mock_client: MagicMock) -> None:
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")

        positions = [
            {"symbol": "BTC-USDT", "size": "0.001", "side": "long"},
            {"symbol": "ETH-USDT", "size": "0.5", "side": "long"},
        ]
        result = await manager.panic_flatten(positions=positions)

        assert result["orders_cancelled"] == 1
        assert result["positions_closed"] == 2
        assert len(manager.get_open_orders()) == 0

    async def test_panic_with_no_positions(self, manager: OrderManager, mock_client: MagicMock) -> None:
        await manager.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        result = await manager.panic_flatten(positions=None)
        assert result["orders_cancelled"] == 1
        assert result["positions_closed"] == 0

    async def test_panic_closes_short_positions_with_buy(self, manager: OrderManager, mock_client: MagicMock) -> None:
        positions = [{"symbol": "BTC-USDT", "size": "0.001", "side": "short"}]
        await manager.panic_flatten(positions=positions)
        # The market order should be a "buy" to close a short
        call_args = mock_client.place_order.call_args_list[-1]
        assert call_args[1]["side"] == "buy"

    async def test_panic_with_empty_state(self, manager: OrderManager) -> None:
        result = await manager.panic_flatten()
        assert result["orders_cancelled"] == 0
        assert result["positions_closed"] == 0


class TestRateLimiting:
    """Test rate limiting behavior."""

    async def test_throttle_allows_requests_within_limit(self, mock_client: MagicMock) -> None:
        mgr = OrderManager(client=mock_client, max_requests_per_window=5, window_seconds=1.0)
        for i in range(5):
            mock_client.place_order.return_value = {
                "order_id": f"ord-{i}", "client_order_id": "", "status_code": "0", "status_msg": ""
            }
            await mgr.place_limit_order("BTC-USDT", "buy", "0.001", "42000")
        assert len(mgr.get_open_orders()) == 5
