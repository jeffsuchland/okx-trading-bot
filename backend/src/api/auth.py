"""API key authentication dependency for FastAPI routes."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, Query


def require_api_key(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
) -> None:
    """FastAPI dependency that enforces API key authentication.

    Checks the X-API-Key header or api_key query parameter against the
    API_SECRET_KEY environment variable.  If API_SECRET_KEY is not set,
    authentication is skipped (development / demo mode).
    """
    secret = os.environ.get("API_SECRET_KEY", "")
    if not secret:
        return

    provided = x_api_key or api_key
    if not provided or provided != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
