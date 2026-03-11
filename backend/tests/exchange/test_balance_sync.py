"""Tests for Account balance synchronization."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.exchange.balance_sync import BalanceSync


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mocked OkxClient."""
    client = MagicMock()
    client.get_account_balance.return_value = {
        "currency": "USDT",
        "available": 1000.50,
        "equity": 1200.75,
        "frozen": 200.25,
    }
    client._account_api.get_positions.return_value = {
        "code": "0",
        "data": [],
    }
    client._check_response.return_value = {"code": "0", "data": []}
    return client


@pytest.fixture
def sync(mock_client: MagicMock) -> BalanceSync:
    """Create a BalanceSync with mocked client."""
    return BalanceSync(client=mock_client, poll_interval=0.1)


class TestGetUsdtBalance:
    """Test get_usdt_balance method."""

    @pytest.mark.asyncio
    async def test_returns_zero_before_first_poll(self, sync: BalanceSync) -> None:
        assert sync.get_usdt_balance() == 0.0

    @pytest.mark.asyncio
    async def test_returns_balance_after_poll(self, sync: BalanceSync) -> None:
        await sync._poll()
        assert sync.get_usdt_balance() == 1000.50


class TestGetTotalEquity:
    """Test get_total_equity method."""

    @pytest.mark.asyncio
    async def test_returns_zero_before_first_poll(self, sync: BalanceSync) -> None:
        assert sync.get_total_equity() == 0.0

    @pytest.mark.asyncio
    async def test_returns_equity_after_poll(self, sync: BalanceSync) -> None:
        await sync._poll()
        assert sync.get_total_equity() == 1200.75


class TestGetPositions:
    """Test get_positions method."""

    @pytest.mark.asyncio
    async def test_returns_empty_before_poll(self, sync: BalanceSync) -> None:
        assert sync.get_positions() == []

    @pytest.mark.asyncio
    async def test_returns_positions_after_sync(self, sync: BalanceSync, mock_client: MagicMock) -> None:
        mock_client._account_api.get_positions.return_value = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT",
                    "pos": "0.001",
                    "avgPx": "42000",
                    "upl": "15.50",
                },
            ],
        }
        await sync._sync_positions()
        positions = sync.get_positions()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTC-USDT"
        assert positions[0]["size"] == 0.001
        assert positions[0]["entry_price"] == 42000.0
        assert positions[0]["unrealized_pnl"] == 15.50
        assert positions[0]["side"] == "long"

    @pytest.mark.asyncio
    async def test_filters_zero_positions(self, sync: BalanceSync, mock_client: MagicMock) -> None:
        mock_client._account_api.get_positions.return_value = {
            "code": "0",
            "data": [
                {"instId": "BTC-USDT", "pos": "0", "avgPx": "0", "upl": "0"},
            ],
        }
        await sync._sync_positions()
        assert sync.get_positions() == []


class TestBalanceUpdatedCallback:
    """Test that balance_updated callback fires on change."""

    @pytest.mark.asyncio
    async def test_callback_fires_on_first_poll(self, mock_client: MagicMock) -> None:
        callback = MagicMock()
        sync = BalanceSync(client=mock_client, poll_interval=0.1, on_balance_updated=callback)
        await sync._poll()
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["usdt_available"] == 1000.50

    @pytest.mark.asyncio
    async def test_callback_does_not_fire_when_unchanged(self, mock_client: MagicMock) -> None:
        callback = MagicMock()
        sync = BalanceSync(client=mock_client, poll_interval=0.1, on_balance_updated=callback)
        await sync._poll()
        await sync._poll()
        # Should only fire once since snapshot didn't change
        assert callback.call_count == 1

    @pytest.mark.asyncio
    async def test_callback_fires_again_on_change(self, mock_client: MagicMock) -> None:
        callback = MagicMock()
        sync = BalanceSync(client=mock_client, poll_interval=0.1, on_balance_updated=callback)
        await sync._poll()

        mock_client.get_account_balance.return_value = {
            "currency": "USDT",
            "available": 900.00,
            "equity": 1100.00,
            "frozen": 200.00,
        }
        await sync._poll()
        assert callback.call_count == 2


class TestApiErrorHandling:
    """Test graceful error handling during sync."""

    @pytest.mark.asyncio
    async def test_poll_survives_api_error(self, sync: BalanceSync, mock_client: MagicMock) -> None:
        mock_client.get_account_balance.side_effect = ConnectionError("timeout")
        await sync._poll()  # Should not raise
        assert sync.get_usdt_balance() == 0.0

    @pytest.mark.asyncio
    async def test_position_sync_survives_api_error(self, sync: BalanceSync, mock_client: MagicMock) -> None:
        mock_client._account_api.get_positions.side_effect = ConnectionError("timeout")
        await sync._sync_positions()  # Should not raise
        assert sync.get_positions() == []


class TestStartStop:
    """Test start and stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self, sync: BalanceSync) -> None:
        task = sync.start()
        assert task is not None
        assert sync._running is True
        await sync.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, sync: BalanceSync) -> None:
        sync.start()
        await sync.stop()
        assert sync._running is False
        assert sync._task is None

    @pytest.mark.asyncio
    async def test_poll_interval_configurable(self, mock_client: MagicMock) -> None:
        sync = BalanceSync(client=mock_client, poll_interval=10.0)
        assert sync._poll_interval == 10.0
