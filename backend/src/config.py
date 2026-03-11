"""Centralized configuration module loading settings from .env."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class Config:
    """Immutable application configuration loaded from environment variables.

    Required vars: OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE.
    Optional vars have defaults documented in .env.example.
    """

    _REQUIRED_VARS = ("OKX_API_KEY", "OKX_SECRET_KEY", "OKX_PASSPHRASE")

    def __init__(self, env_path: str | None = None) -> None:
        if env_path:
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(override=True)

        self._validate_required()

        # OKX credentials
        self.okx_api_key: str = os.environ["OKX_API_KEY"]
        self.okx_secret_key: str = os.environ["OKX_SECRET_KEY"]
        self.okx_passphrase: str = os.environ["OKX_PASSPHRASE"]
        self.okx_sandbox: bool = os.getenv("OKX_SANDBOX", "true").lower() == "true"

        # Trading defaults
        self.trading_pair: str = os.getenv("TRADING_PAIR", "BTC-USDT")
        self.strategy_name: str = os.getenv("STRATEGY_NAME", "MeanReversionStrategy")
        self.spend_per_trade: float = float(os.getenv("SPEND_PER_TRADE", "10"))
        self.max_exposure: float = float(os.getenv("MAX_EXPOSURE", "100"))

        # Risk parameters
        self.stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "2.0"))
        self.stop_loss_mode: str = os.getenv("STOP_LOSS_MODE", "fixed")
        self.max_drawdown_pct: float = float(os.getenv("MAX_DRAWDOWN_PCT", "5.0"))
        self.daily_loss_limit: float = float(os.getenv("DAILY_LOSS_LIMIT", "50.0"))

        # Server settings
        self.server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
        self.server_port: int = int(os.getenv("SERVER_PORT", "8000"))

        # Tick interval
        self.tick_interval: float = float(os.getenv("TICK_INTERVAL", "5.0"))

        self._frozen = True

    def _validate_required(self) -> None:
        """Raise ConfigError if any required env vars are missing."""
        missing = [var for var in self._REQUIRED_VARS if not os.environ.get(var)]
        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please set them in your .env file or environment."
            )

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError(f"Config is immutable after initialization. Cannot set '{name}'.")
        super().__setattr__(name, value)

    def get_trading_config(self) -> dict[str, Any]:
        """Return a dict suitable for strategy and risk manager initialization."""
        return {
            "trading_pair": self.trading_pair,
            "strategy_name": self.strategy_name,
            "spend_per_trade": self.spend_per_trade,
            "max_total_exposure": self.max_exposure,
            "stop_loss_pct": self.stop_loss_pct,
            "stop_loss_mode": self.stop_loss_mode,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_daily_loss": self.daily_loss_limit,
        }

    def get_okx_credentials(self) -> dict[str, str]:
        """Return OKX API credentials dict."""
        return {
            "api_key": self.okx_api_key,
            "secret_key": self.okx_secret_key,
            "passphrase": self.okx_passphrase,
            "sandbox": str(self.okx_sandbox),
        }

    def get_server_config(self) -> dict[str, Any]:
        """Return server configuration dict."""
        return {
            "host": self.server_host,
            "port": self.server_port,
        }
