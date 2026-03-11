"""FastAPI REST API routes for the dashboard."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


_start_time = time.time()


class ConfigUpdate(BaseModel):
    """Request body for PUT /api/config."""
    strategy: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None


def create_router(deps: dict[str, Any]) -> APIRouter:
    """Create API router with injected dependencies.

    Args:
        deps: Dict with keys: trading_loop, risk_manager, balance_sync, pnl_tracker, strategy, config.
    """
    router = APIRouter()

    @router.get("/health")
    def get_health() -> dict[str, Any]:
        return {"status": "ok"}

    @router.get("/status")
    def get_status() -> dict[str, Any]:
        trading_loop = deps.get("trading_loop")
        strategy = deps.get("strategy")
        status = "stopped"
        if trading_loop is not None:
            status = trading_loop.status
        strategy_name = ""
        if strategy is not None:
            strategy_name = type(strategy).__name__
        return {
            "status": status,
            "uptime": round(time.time() - _start_time, 1),
            "active_strategy": strategy_name,
            "heartbeat_ts": datetime.now(timezone.utc).isoformat(),
        }

    @router.get("/balance")
    def get_balance() -> dict[str, Any]:
        balance_sync = deps.get("balance_sync")
        if balance_sync is None:
            return {"usdt_available": 0.0, "total_equity": 0.0, "positions": []}
        return {
            "usdt_available": balance_sync.get_usdt_balance(),
            "total_equity": balance_sync.get_total_equity(),
            "positions": balance_sync.get_positions(),
        }

    @router.get("/pnl")
    def get_pnl() -> dict[str, Any]:
        pnl_tracker = deps.get("pnl_tracker")
        if pnl_tracker is None:
            return {"daily_pnl": 0.0, "cumulative_pnl": 0.0, "win_rate": 0.0, "recent_trades": []}
        wl = pnl_tracker.get_win_loss_ratio()
        return {
            "daily_pnl": pnl_tracker.get_daily_pnl(),
            "cumulative_pnl": pnl_tracker.get_cumulative_pnl(),
            "win_rate": wl.get("win_rate", 0.0),
            "recent_trades": pnl_tracker.get_recent_trades(10),
        }

    @router.get("/config")
    def get_config() -> dict[str, Any]:
        strategy = deps.get("strategy")
        risk_manager = deps.get("risk_manager")
        result: dict[str, Any] = {"strategy": {}, "risk": {}}
        if strategy is not None:
            result["strategy"] = {
                "name": type(strategy).__name__,
                "config": strategy.config,
            }
        if risk_manager is not None:
            result["risk"] = risk_manager.get_risk_status()
        return result

    @router.put("/config")
    def put_config(body: ConfigUpdate) -> dict[str, Any]:
        strategy = deps.get("strategy")
        risk_manager = deps.get("risk_manager")
        if body.strategy and strategy is not None:
            strategy.update_config(body.strategy)
        if body.risk and risk_manager is not None:
            risk_manager.update_config(body.risk)
        return {"success": True}

    @router.post("/panic")
    def post_panic() -> dict[str, Any]:
        risk_manager = deps.get("risk_manager")
        if risk_manager is None:
            raise HTTPException(status_code=503, detail="Risk manager not available")
        risk_manager.panic()
        return {"success": True, "message": "Panic mode activated"}

    @router.post("/start")
    async def post_start() -> dict[str, Any]:
        trading_loop = deps.get("trading_loop")
        if trading_loop is None:
            raise HTTPException(status_code=503, detail="Trading loop not available")
        trading_loop.start()
        return {"success": True, "status": "running"}

    @router.post("/stop")
    async def post_stop() -> dict[str, Any]:
        trading_loop = deps.get("trading_loop")
        if trading_loop is None:
            raise HTTPException(status_code=503, detail="Trading loop not available")
        await trading_loop.stop()
        return {"success": True, "status": "stopped"}

    return router
