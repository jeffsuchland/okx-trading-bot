"""Tests for centralized configuration module."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

from src.config import Config, ConfigError


def _write_env(path: str, content: str) -> str:
    """Write a .env file and return its path."""
    env_path = os.path.join(path, ".env.test")
    with open(env_path, "w") as f:
        f.write(content)
    return env_path


_VALID_ENV = """\
OKX_API_KEY=test-key-123
OKX_SECRET_KEY=test-secret-456
OKX_PASSPHRASE=test-pass-789
SPEND_PER_TRADE=25
MAX_EXPOSURE=200
STOP_LOSS_PCT=3.5
MAX_DRAWDOWN_PCT=8.0
DAILY_LOSS_LIMIT=100
SERVER_PORT=9000
"""


class TestConfigLoading:
    """Verify Config loads env vars via python-dotenv."""

    def test_loads_required_vars(self, tmp_path: Any) -> None:
        env_path = _write_env(str(tmp_path), _VALID_ENV)
        cfg = Config(env_path=env_path)
        assert cfg.okx_api_key == "test-key-123"
        assert cfg.okx_secret_key == "test-secret-456"
        assert cfg.okx_passphrase == "test-pass-789"

    def test_loads_optional_vars_with_custom_values(self, tmp_path: Any) -> None:
        env_path = _write_env(str(tmp_path), _VALID_ENV)
        cfg = Config(env_path=env_path)
        assert cfg.spend_per_trade == 25.0
        assert cfg.max_exposure == 200.0
        assert cfg.stop_loss_pct == 3.5
        assert cfg.max_drawdown_pct == 8.0
        assert cfg.daily_loss_limit == 100.0
        assert cfg.server_port == 9000


class TestMissingRequired:
    """Verify ConfigError raised for missing required vars."""

    def test_missing_api_key(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        env_content = "OKX_SECRET_KEY=secret\nOKX_PASSPHRASE=pass\n"
        env_path = _write_env(str(tmp_path), env_content)
        # Clear any pre-existing env vars
        monkeypatch.delenv("OKX_API_KEY", raising=False)
        with pytest.raises(ConfigError, match="OKX_API_KEY"):
            Config(env_path=env_path)

    def test_missing_multiple_vars(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        env_path = _write_env(str(tmp_path), "# empty\n")
        monkeypatch.delenv("OKX_API_KEY", raising=False)
        monkeypatch.delenv("OKX_SECRET_KEY", raising=False)
        monkeypatch.delenv("OKX_PASSPHRASE", raising=False)
        with pytest.raises(ConfigError, match="OKX_API_KEY"):
            Config(env_path=env_path)

    def test_error_message_is_clear(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        env_path = _write_env(str(tmp_path), "OKX_API_KEY=key\n")
        monkeypatch.delenv("OKX_SECRET_KEY", raising=False)
        monkeypatch.delenv("OKX_PASSPHRASE", raising=False)
        with pytest.raises(ConfigError) as exc_info:
            Config(env_path=env_path)
        msg = str(exc_info.value)
        assert "OKX_SECRET_KEY" in msg
        assert "OKX_PASSPHRASE" in msg
        assert ".env" in msg


class TestDefaults:
    """Verify default values for optional vars."""

    def test_defaults_when_not_set(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        # Clear any env vars that may have been set by previous tests loading _VALID_ENV
        for var in [
            "SPEND_PER_TRADE", "MAX_EXPOSURE", "STOP_LOSS_PCT", "MAX_DRAWDOWN_PCT",
            "DAILY_LOSS_LIMIT", "TRADING_PAIR", "STRATEGY_NAME", "SERVER_HOST",
            "SERVER_PORT", "TICK_INTERVAL", "OKX_SANDBOX", "DEMO_MODE",
        ]:
            monkeypatch.delenv(var, raising=False)
        env_content = "OKX_API_KEY=k\nOKX_SECRET_KEY=s\nOKX_PASSPHRASE=p\n"
        env_path = _write_env(str(tmp_path), env_content)
        cfg = Config(env_path=env_path)
        assert cfg.spend_per_trade == 10.0
        assert cfg.max_exposure == 100.0
        assert cfg.stop_loss_pct == 2.0
        assert cfg.max_drawdown_pct == 5.0
        assert cfg.daily_loss_limit == 50.0
        assert cfg.trading_pair == "BTC-USDT"
        assert cfg.strategy_name == "MeanReversionStrategy"
        assert cfg.server_host == "127.0.0.1"
        assert cfg.server_port == 8000
        assert cfg.tick_interval == 5.0
        assert cfg.okx_sandbox is True


class TestGetTradingConfig:
    """Verify get_trading_config() returns dict for strategy/risk init."""

    def test_returns_trading_dict(self, tmp_path: Any) -> None:
        env_path = _write_env(str(tmp_path), _VALID_ENV)
        cfg = Config(env_path=env_path)
        tc = cfg.get_trading_config()
        assert isinstance(tc, dict)
        assert tc["trading_pair"] == "BTC-USDT"
        assert tc["strategy_name"] == "MeanReversionStrategy"
        assert tc["spend_per_trade"] == 25.0
        assert tc["max_total_exposure"] == 200.0
        assert tc["stop_loss_pct"] == 3.5
        assert tc["max_drawdown_pct"] == 8.0
        assert tc["max_daily_loss"] == 100.0


class TestImmutability:
    """Verify Config is immutable after initialization."""

    def test_cannot_set_attribute(self, tmp_path: Any) -> None:
        env_path = _write_env(str(tmp_path), _VALID_ENV)
        cfg = Config(env_path=env_path)
        with pytest.raises(AttributeError, match="immutable"):
            cfg.spend_per_trade = 999.0

    def test_cannot_add_new_attribute(self, tmp_path: Any) -> None:
        env_path = _write_env(str(tmp_path), _VALID_ENV)
        cfg = Config(env_path=env_path)
        with pytest.raises(AttributeError, match="immutable"):
            cfg.new_field = "something"


class TestEnvExample:
    """Verify .env.example exists and documents all vars."""

    def test_env_example_exists(self) -> None:
        env_example = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        assert os.path.exists(env_example), ".env.example should exist"

    def test_env_example_lists_all_vars(self) -> None:
        env_example = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_example) as f:
            content = f.read()
        required_vars = ["OKX_API_KEY", "OKX_SECRET_KEY", "OKX_PASSPHRASE"]
        optional_vars = [
            "OKX_SANDBOX", "TRADING_PAIR", "STRATEGY_NAME",
            "SPEND_PER_TRADE", "MAX_EXPOSURE", "STOP_LOSS_PCT",
            "STOP_LOSS_MODE", "MAX_DRAWDOWN_PCT", "DAILY_LOSS_LIMIT",
            "SERVER_HOST", "SERVER_PORT", "TICK_INTERVAL",
        ]
        for var in required_vars + optional_vars:
            assert var in content, f"{var} should be documented in .env.example"
