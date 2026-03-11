"""FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import create_router


def create_app(dependencies: dict[str, Any] | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        dependencies: Dict of shared bot components (trading_loop, risk_manager, etc.)
    """
    app = FastAPI(title="OKX Trading Bot", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    deps = dependencies or {}
    app.state.deps = deps

    router = create_router(deps)
    app.include_router(router, prefix="/api")

    return app
