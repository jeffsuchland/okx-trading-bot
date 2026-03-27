"""Tests for FastAPI backend REST API routes."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


def _make_deps() -> dict[str, Any]:
    """Create mock dependencies for the API."""
    trading_loop = MagicMock()
    trading_loop.status = "running"
    trading_loop.start = MagicMock()
    trading_loop.stop = AsyncMock()

    strategy = MagicMock()
    strategy.__class__.__name__ = "MeanReversionStrategy"
    strategy.config = {"rsi_period": 14, "rsi_oversold": 30}
    strategy.update_config = MagicMock()

    risk_manager = MagicMock()
    risk_manager.panic = AsyncMock()
    risk_manager.update_config = MagicMock()
    risk_manager.get_risk_status = MagicMock(return_value={
        "halted": False,
        "current_exposure": 42.0,
        "circuit_breaker": {"triggered": False, "drawdown_pct": 1.0},
        "daily_limit": {"is_halted": False},
        "stop_loss_levels": {},
    })

    balance_sync = MagicMock()
    balance_sync.get_usdt_balance = MagicMock(return_value=1000.0)
    balance_sync.get_total_equity = MagicMock(return_value=1500.0)
    balance_sync.get_balances = MagicMock(return_value=[
        {"ccy": "USDT", "availBal": "1000.0", "eq": "1500.0"},
    ])
    balance_sync.get_positions = MagicMock(return_value=[
        {"symbol": "BTC-USDT", "size": "0.01"},
    ])

    pnl_tracker = MagicMock()
    pnl_tracker.get_daily_pnl = MagicMock(return_value=15.5)
    pnl_tracker.get_cumulative_pnl = MagicMock(return_value=120.0)
    pnl_tracker.get_win_loss_ratio = MagicMock(return_value={
        "wins": 10, "losses": 5, "total": 15, "win_rate": 66.67,
    })
    pnl_tracker.get_recent_trades = MagicMock(return_value=[
        {"symbol": "BTC-USDT", "side": "buy", "pnl": 5.0},
    ])

    return {
        "trading_loop": trading_loop,
        "strategy": strategy,
        "risk_manager": risk_manager,
        "balance_sync": balance_sync,
        "pnl_tracker": pnl_tracker,
    }


@pytest.fixture
def deps() -> dict[str, Any]:
    return _make_deps()


@pytest.fixture
def client(deps: dict[str, Any]) -> TestClient:
    app = create_app(dependencies=deps)
    return TestClient(app)


@pytest.fixture
def empty_client() -> TestClient:
    app = create_app(dependencies={})
    return TestClient(app)


class TestGetStatus:
    """Test GET /api/status."""

    def test_returns_correct_schema(self, client: TestClient) -> None:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "uptime" in data
        assert "active_strategy" in data
        assert "heartbeat_ts" in data

    def test_returns_running_status(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        assert data["status"] == "running"
        assert data["active_strategy"] == "MeanReversionStrategy"

    def test_returns_stopped_without_loop(self, empty_client: TestClient) -> None:
        data = empty_client.get("/api/status").json()
        assert data["status"] == "stopped"


class TestGetBalance:
    """Test GET /api/balance."""

    def test_returns_correct_schema(self, client: TestClient) -> None:
        resp = client.get("/api/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert "usdt_available" in data
        assert "total_equity" in data
        assert "positions" in data

    def test_returns_balances(self, client: TestClient) -> None:
        data = client.get("/api/balance").json()
        assert data["usdt_available"] == 1000.0
        assert data["total_equity"] == 1500.0
        assert len(data["positions"]) == 1

    def test_returns_zeros_without_sync(self, empty_client: TestClient) -> None:
        data = empty_client.get("/api/balance").json()
        assert data["usdt_available"] == 0.0


class TestGetPnl:
    """Test GET /api/pnl."""

    def test_returns_correct_schema(self, client: TestClient) -> None:
        resp = client.get("/api/pnl")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_pnl" in data
        assert "cumulative_pnl" in data
        assert "win_rate" in data
        assert "recent_trades" in data

    def test_returns_pnl_data(self, client: TestClient) -> None:
        data = client.get("/api/pnl").json()
        assert data["daily_pnl"] == 15.5
        assert data["cumulative_pnl"] == 120.0
        assert data["win_rate"] == 66.67
        assert len(data["recent_trades"]) == 1


class TestGetConfig:
    """Test GET /api/config."""

    def test_returns_strategy_and_risk(self, client: TestClient) -> None:
        data = client.get("/api/config").json()
        assert "strategy" in data
        assert "risk" in data
        assert data["strategy"]["name"] == "MeanReversionStrategy"
        assert data["strategy"]["config"]["rsi_period"] == 14


class TestPutConfig:
    """Test PUT /api/config."""

    def test_updates_config(self, client: TestClient, deps: dict[str, Any]) -> None:
        resp = client.put("/api/config", json={"strategy": {"rsi_period": 21}, "risk": {"spend_per_trade": 20}})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        deps["strategy"].update_config.assert_called_once_with({"rsi_period": 21})
        deps["risk_manager"].update_config.assert_called_once_with({"spend_per_trade": 20})

    def test_partial_update(self, client: TestClient, deps: dict[str, Any]) -> None:
        resp = client.put("/api/config", json={"risk": {"max_drawdown_pct": 10}})
        assert resp.status_code == 200
        deps["risk_manager"].update_config.assert_called_once()


class TestPostPanic:
    """Test POST /api/panic."""

    def test_triggers_panic(self, client: TestClient, deps: dict[str, Any]) -> None:
        resp = client.post("/api/panic")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        deps["risk_manager"].panic.assert_called_once()

    def test_503_without_risk_manager(self, empty_client: TestClient) -> None:
        resp = empty_client.post("/api/panic")
        assert resp.status_code == 503


class TestPostStartStop:
    """Test POST /api/start and POST /api/stop."""

    def test_start(self, client: TestClient, deps: dict[str, Any]) -> None:
        resp = client.post("/api/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        deps["trading_loop"].start.assert_called_once()

    def test_stop(self, client: TestClient, deps: dict[str, Any]) -> None:
        resp = client.post("/api/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_start_503_without_loop(self, empty_client: TestClient) -> None:
        resp = empty_client.post("/api/start")
        assert resp.status_code == 503

    def test_stop_503_without_loop(self, empty_client: TestClient) -> None:
        resp = empty_client.post("/api/stop")
        assert resp.status_code == 503


class TestInvalidConfig:
    """Test PUT /api/config with invalid payloads."""

    def test_invalid_config_type_returns_422(self, client: TestClient) -> None:
        resp = client.put("/api/config", json={"strategy": "not-a-dict"})
        assert resp.status_code == 422

    def test_invalid_risk_type_returns_422(self, client: TestClient) -> None:
        resp = client.put("/api/config", json={"risk": 123})
        assert resp.status_code == 422

    def test_non_json_body_returns_422(self, client: TestClient) -> None:
        resp = client.put("/api/config", content=b"not json", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422

    def test_empty_config_succeeds(self, client: TestClient) -> None:
        resp = client.put("/api/config", json={})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestSchemaConformance:
    """Verify response schemas match what the frontend expects."""

    def test_status_schema_keys(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        expected_keys = {"status", "uptime", "active_strategy", "heartbeat_ts"}
        assert expected_keys.issubset(set(data.keys()))
        assert isinstance(data["status"], str)
        assert isinstance(data["uptime"], (int, float))
        assert isinstance(data["active_strategy"], str)
        assert isinstance(data["heartbeat_ts"], str)

    def test_balance_schema_keys(self, client: TestClient) -> None:
        data = client.get("/api/balance").json()
        expected_keys = {"usdt_available", "total_equity", "positions"}
        assert expected_keys.issubset(set(data.keys()))
        assert isinstance(data["usdt_available"], (int, float))
        assert isinstance(data["total_equity"], (int, float))
        assert isinstance(data["positions"], list)

    def test_pnl_schema_keys(self, client: TestClient) -> None:
        data = client.get("/api/pnl").json()
        expected_keys = {"daily_pnl", "cumulative_pnl", "win_rate", "recent_trades"}
        assert expected_keys.issubset(set(data.keys()))
        assert isinstance(data["daily_pnl"], (int, float))
        assert isinstance(data["cumulative_pnl"], (int, float))
        assert isinstance(data["win_rate"], (int, float))
        assert isinstance(data["recent_trades"], list)

    def test_config_schema_keys(self, client: TestClient) -> None:
        data = client.get("/api/config").json()
        assert "strategy" in data
        assert "risk" in data
        assert isinstance(data["strategy"], dict)
        assert isinstance(data["risk"], dict)


class TestCORS:
    """Test CORS middleware."""

    def test_cors_allows_localhost_5173(self, client: TestClient) -> None:
        resp = client.options(
            "/api/status",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
