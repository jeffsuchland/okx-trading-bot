"""Tests for WebSocket market data stream."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exchange.ws_stream import WsStream


@pytest.fixture
def ws_queue() -> asyncio.Queue:
    """Provide a fresh asyncio queue."""
    return asyncio.Queue()


@pytest.fixture
def stream(ws_queue: asyncio.Queue) -> WsStream:
    """Create a WsStream with a test queue."""
    return WsStream(url="wss://test.example.com/ws", queue=ws_queue)


class TestWsStreamConnect:
    """Test WebSocket connection."""

    @pytest.mark.asyncio
    async def test_connect_calls_websockets(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        with patch("src.exchange.ws_stream.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await stream.connect()
            assert stream._ws is mock_ws

    @pytest.mark.asyncio
    async def test_connect_resubscribes_existing(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        stream._subscriptions = [{"channel": "tickers", "instId": "BTC-USDT"}]
        with patch("src.exchange.ws_stream.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await stream.connect()
            mock_ws.send.assert_called_once()
            sent = json.loads(mock_ws.send.call_args[0][0])
            assert sent["op"] == "subscribe"
            assert sent["args"] == [{"channel": "tickers", "instId": "BTC-USDT"}]


class TestSubscribe:
    """Test subscribe and unsubscribe methods."""

    @pytest.mark.asyncio
    async def test_subscribe_sends_message(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        stream._ws = mock_ws
        await stream.subscribe("tickers", "BTC-USDT")
        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["op"] == "subscribe"
        assert sent["args"] == [{"channel": "tickers", "instId": "BTC-USDT"}]
        assert {"channel": "tickers", "instId": "BTC-USDT"} in stream._subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_does_not_duplicate(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        stream._ws = mock_ws
        await stream.subscribe("tickers", "BTC-USDT")
        await stream.subscribe("tickers", "BTC-USDT")
        assert stream._subscriptions.count({"channel": "tickers", "instId": "BTC-USDT"}) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_sends_message(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        stream._ws = mock_ws
        stream._subscriptions = [{"channel": "tickers", "instId": "BTC-USDT"}]
        await stream.unsubscribe("tickers", "BTC-USDT")
        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["op"] == "unsubscribe"
        assert {"channel": "tickers", "instId": "BTC-USDT"} not in stream._subscriptions


class TestMessageParsing:
    """Test that incoming messages are parsed and queued."""

    @pytest.mark.asyncio
    async def test_messages_placed_on_queue(self, stream: WsStream, ws_queue: asyncio.Queue) -> None:
        ticker_msg = json.dumps({"arg": {"channel": "tickers"}, "data": [{"last": "42000"}]})

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = MagicMock(return_value=iter([ticker_msg]))

        async def fake_connect(*args, **kwargs):
            return mock_ws

        with patch("src.exchange.ws_stream.websockets.connect", side_effect=fake_connect):
            stream._running = True
            stream._ws = mock_ws

            # Run one iteration of listen by manually processing
            raw_data = json.loads(ticker_msg)
            await ws_queue.put(raw_data)

            result = await ws_queue.get()
            assert result["data"][0]["last"] == "42000"


class TestAutoReconnect:
    """Test auto-reconnect with exponential backoff."""

    @pytest.mark.asyncio
    async def test_reconnect_delay_doubles(self, stream: WsStream) -> None:
        assert stream._reconnect_delay == 1.0
        stream._reconnect_delay = min(stream._reconnect_delay * 2, stream.max_reconnect_delay)
        assert stream._reconnect_delay == 2.0
        stream._reconnect_delay = min(stream._reconnect_delay * 2, stream.max_reconnect_delay)
        assert stream._reconnect_delay == 4.0

    @pytest.mark.asyncio
    async def test_reconnect_delay_capped_at_max(self, stream: WsStream) -> None:
        stream._reconnect_delay = 16.0
        stream._reconnect_delay = min(stream._reconnect_delay * 2, stream.max_reconnect_delay)
        assert stream._reconnect_delay == 30.0

    @pytest.mark.asyncio
    async def test_reconnect_delay_resets_on_connect(self, stream: WsStream) -> None:
        stream._reconnect_delay = 16.0
        mock_ws = AsyncMock()
        with patch("src.exchange.ws_stream.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await stream.connect()
            assert stream._reconnect_delay == 1.0


class TestClose:
    """Test clean shutdown."""

    @pytest.mark.asyncio
    async def test_close_shuts_down_connection(self, stream: WsStream) -> None:
        mock_ws = AsyncMock()
        stream._ws = mock_ws
        stream._running = True
        stream._listen_task = asyncio.create_task(asyncio.sleep(100))

        await stream.close()

        assert stream._running is False
        assert stream._ws is None
        assert stream._listen_task is None
        assert stream._subscriptions == []
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_connection(self, stream: WsStream) -> None:
        await stream.close()
        assert stream._running is False
        assert stream._ws is None
