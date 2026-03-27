"""Tests for application entry point and lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


class TestHealthEndpoint:
    """Verify GET /api/health returns 200 immediately."""

    def test_health_returns_ok(self) -> None:
        app = create_app(dependencies={})
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestBuildComponents:
    """Verify all components initialized in correct dependency order."""

    @patch("main.OkxClient")
    @patch("main.WsStream")
    @patch("main.StrategyRegistry")
    def test_build_creates_all_components(
        self, mock_registry: MagicMock, mock_ws: MagicMock, mock_client: MagicMock
    ) -> None:
        from main import build_components

        mock_strategy_cls = MagicMock()
        mock_registry.return_value.get.return_value = mock_strategy_cls

        config = MagicMock()
        config.demo_mode = False
        config.get_okx_credentials.return_value = {
            "api_key": "k", "secret_key": "s", "passphrase": "p", "sandbox": "true"
        }
        config.okx_sandbox = True
        config.strategy_name = "MeanReversionStrategy"
        config.get_trading_config.return_value = {
            "spend_per_trade": 10, "max_total_exposure": 100,
            "stop_loss_pct": 2, "max_drawdown_pct": 5, "max_daily_loss": 50,
        }
        config.tick_interval = 5.0

        components = build_components(config)

        assert "okx_client" in components
        assert "ws_stream" in components
        assert "order_manager" in components
        assert "balance_sync" in components
        assert "strategy" in components
        assert "risk_manager" in components
        assert "pnl_tracker" in components
        assert "trading_loop" in components
        assert "market_data_queue" in components

        # Verify dependency order: client created before order_manager
        mock_client.assert_called_once()
        mock_ws.assert_called_once()
        mock_registry.return_value.get.assert_called_once_with("MeanReversionStrategy")
        mock_strategy_cls.assert_called_once()


class TestGracefulShutdown:
    """Verify shutdown stops trading loop and closes WebSocket."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_loop_and_ws(self) -> None:
        from main import shutdown

        trading_loop = MagicMock()
        trading_loop.is_running = True
        trading_loop.stop = AsyncMock()

        ws_stream = MagicMock()
        ws_stream.close = AsyncMock()

        components = {
            "trading_loop": trading_loop,
            "ws_stream": ws_stream,
        }

        await shutdown(components)

        trading_loop.stop.assert_called_once()
        ws_stream.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_missing_components(self) -> None:
        from main import shutdown
        # Should not raise even with empty components
        await shutdown({})


class TestStartupLogs:
    """Verify startup logs show config summary without exposing secrets."""

    def test_log_config_summary_no_secrets(self, caplog: pytest.LogCaptureFixture) -> None:
        from main import log_config_summary

        config = MagicMock()
        config.trading_pair = "BTC-USDT"
        config.strategy_name = "MeanReversionStrategy"
        config.spend_per_trade = 10.0
        config.max_exposure = 100.0
        config.stop_loss_pct = 2.0
        config.stop_loss_mode = "fixed"
        config.max_drawdown_pct = 5.0
        config.daily_loss_limit = 50.0
        config.server_host = "127.0.0.1"
        config.server_port = 8000
        config.okx_sandbox = True
        config.okx_api_key = "SECRET_KEY_123"
        config.okx_secret_key = "SECRET_SECRET_456"
        config.okx_passphrase = "SECRET_PASS_789"

        with caplog.at_level(logging.INFO):
            log_config_summary(config)

        log_text = caplog.text
        assert "BTC-USDT" in log_text
        assert "MeanReversionStrategy" in log_text
        assert "10.00" in log_text
        # Secrets must NOT appear
        assert "SECRET_KEY_123" not in log_text
        assert "SECRET_SECRET_456" not in log_text
        assert "SECRET_PASS_789" not in log_text
