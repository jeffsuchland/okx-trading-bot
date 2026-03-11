"""WebSocket market data stream for OKX public channels."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)

OKX_WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"


class WsStream:
    """Manages a WebSocket connection to OKX public market data channels."""

    def __init__(
        self,
        url: str = OKX_WS_PUBLIC_URL,
        max_reconnect_delay: float = 30.0,
        queue: asyncio.Queue[dict[str, Any]] | None = None,
    ) -> None:
        self.url = url
        self.max_reconnect_delay = max_reconnect_delay
        self.queue: asyncio.Queue[dict[str, Any]] = queue or asyncio.Queue()
        self._ws: WebSocketClientProtocol | None = None
        self._subscriptions: list[dict[str, str]] = []
        self._running = False
        self._listen_task: asyncio.Task[None] | None = None
        self._reconnect_delay = 1.0

    async def connect(self) -> None:
        """Establish WebSocket connection to OKX."""
        self._ws = await websockets.connect(self.url)
        self._reconnect_delay = 1.0
        logger.info("WebSocket connected to %s", self.url)

        # Re-subscribe to any existing subscriptions after reconnect
        if self._subscriptions:
            await self._send_subscribe(self._subscriptions)

    async def _send_subscribe(self, args: list[dict[str, str]]) -> None:
        """Send a subscribe message over the WebSocket."""
        if self._ws is None:
            return
        msg = json.dumps({"op": "subscribe", "args": args})
        await self._ws.send(msg)
        logger.info("Subscribed to %s", args)

    async def _send_unsubscribe(self, args: list[dict[str, str]]) -> None:
        """Send an unsubscribe message over the WebSocket."""
        if self._ws is None:
            return
        msg = json.dumps({"op": "unsubscribe", "args": args})
        await self._ws.send(msg)
        logger.info("Unsubscribed from %s", args)

    async def subscribe(self, channel: str, instrument_id: str) -> None:
        """Subscribe to a channel for a given instrument."""
        arg = {"channel": channel, "instId": instrument_id}
        if arg not in self._subscriptions:
            self._subscriptions.append(arg)
        await self._send_subscribe([arg])

    async def unsubscribe(self, channel: str, instrument_id: str) -> None:
        """Unsubscribe from a channel for a given instrument."""
        arg = {"channel": channel, "instId": instrument_id}
        if arg in self._subscriptions:
            self._subscriptions.remove(arg)
        await self._send_unsubscribe([arg])

    async def _listen(self) -> None:
        """Listen for incoming messages and place them on the queue."""
        while self._running:
            try:
                if self._ws is None:
                    await self.connect()

                assert self._ws is not None
                async for raw_msg in self._ws:
                    if not self._running:
                        break
                    try:
                        data = json.loads(raw_msg)
                        await self.queue.put(data)
                    except json.JSONDecodeError:
                        logger.warning("Received non-JSON message: %s", raw_msg[:100])

            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedError,
                ConnectionError,
                OSError,
            ) as e:
                if not self._running:
                    break
                logger.warning(
                    "WebSocket disconnected: %s. Reconnecting in %.1fs...",
                    e,
                    self._reconnect_delay,
                )
                self._ws = None
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.max_reconnect_delay
                )
            except Exception:
                if not self._running:
                    break
                logger.exception("Unexpected error in WebSocket listener")
                self._ws = None
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self.max_reconnect_delay
                )

    def start(self) -> asyncio.Task[None]:
        """Start the WebSocket listener loop."""
        self._running = True
        self._listen_task = asyncio.create_task(self._listen())
        return self._listen_task

    async def close(self) -> None:
        """Cleanly shut down the WebSocket connection."""
        self._running = False
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        self._subscriptions.clear()
        logger.info("WebSocket stream closed")
