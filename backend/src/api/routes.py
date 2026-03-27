"""FastAPI REST API routes for the dashboard."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from src.api.auth import require_api_key


_start_time = time.time()


class RiskConfigUpdate(BaseModel):
    """Validated risk fields for PUT /api/config."""

    spend_per_trade: float | None = None
    max_exposure: float | None = None
    stop_loss_pct: float | None = None
    max_drawdown_pct: float | None = None
    daily_loss_limit: float | None = None

    @field_validator("spend_per_trade", "max_exposure", "daily_loss_limit", mode="before")
    @classmethod
    def must_be_non_negative(cls, v: Any) -> Any:
        if v is not None and float(v) < 0:
            raise ValueError("must be a non-negative number")
        return v

    @field_validator("stop_loss_pct", "max_drawdown_pct", mode="before")
    @classmethod
    def must_be_percentage(cls, v: Any) -> Any:
        if v is not None:
            fv = float(v)
            if fv < 0 or fv > 100:
                raise ValueError("must be between 0 and 100")
        return v

    model_config = {"extra": "allow"}


class ConfigUpdate(BaseModel):
    """Request body for PUT /api/config."""

    strategy: dict[str, Any] | None = None
    risk: RiskConfigUpdate | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_risk(cls, values: Any) -> Any:
        if isinstance(values, dict) and "risk" in values and isinstance(values["risk"], dict):
            values["risk"] = RiskConfigUpdate(**values["risk"])
        return values


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

    @router.put("/config", dependencies=[Depends(require_api_key)])
    def put_config(body: ConfigUpdate) -> dict[str, Any]:
        strategy = deps.get("strategy")
        risk_manager = deps.get("risk_manager")
        if body.strategy and strategy is not None:
            strategy.update_config(body.strategy)
        if body.risk and risk_manager is not None:
            risk_manager.update_config(body.risk.model_dump(exclude_none=True))
        return {"success": True}

    @router.post("/panic", dependencies=[Depends(require_api_key)])
    def post_panic() -> dict[str, Any]:
        risk_manager = deps.get("risk_manager")
        if risk_manager is None:
            raise HTTPException(status_code=503, detail="Risk manager not available")
        risk_manager.panic()
        return {"success": True, "message": "Panic mode activated"}

    @router.post("/start", dependencies=[Depends(require_api_key)])
    async def post_start() -> dict[str, Any]:
        trading_loop = deps.get("trading_loop")
        if trading_loop is None:
            raise HTTPException(status_code=503, detail="Trading loop not available")
        trading_loop.start()
        return {"success": True, "status": "running"}

    @router.post("/stop", dependencies=[Depends(require_api_key)])
    async def post_stop() -> dict[str, Any]:
        trading_loop = deps.get("trading_loop")
        if trading_loop is None:
            raise HTTPException(status_code=503, detail="Trading loop not available")
        await trading_loop.stop()
        return {"success": True, "status": "stopped"}

    return router
