"""Tests for the structured logging system."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pytest

from src.logging_config import (
    ColoredConsoleFormatter,
    JsonFormatter,
    get_logger,
    setup_logging,
)


class TestJsonFormatter:
    """Verify JSON formatter outputs correct structure."""

    def test_formats_as_json(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_component",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["component"] == "test_component"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_includes_extra_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="trading",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Order placed",
            args=None,
            exc_info=None,
        )
        record.trade_id = "t-001"  # type: ignore[attr-defined]
        record.symbol = "BTC-USDT"  # type: ignore[attr-defined]
        record.side = "buy"  # type: ignore[attr-defined]
        record.qty = "0.001"  # type: ignore[attr-defined]
        record.price = "42000"  # type: ignore[attr-defined]

        output = formatter.format(record)
        data = json.loads(output)
        assert data["trade_id"] == "t-001"
        assert data["symbol"] == "BTC-USDT"
        assert data["side"] == "buy"
        assert data["qty"] == "0.001"
        assert data["price"] == "42000"

    def test_includes_exception(self) -> None:
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Something failed",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestColoredConsoleFormatter:
    """Verify console formatter outputs human-readable text."""

    def test_formats_readable(self) -> None:
        formatter = ColoredConsoleFormatter()
        record = logging.LogRecord(
            name="risk_manager",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Stop-loss triggered",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        assert "WARNING" in output
        assert "risk_manager" in output
        assert "Stop-loss triggered" in output

    def test_includes_extras_in_output(self) -> None:
        formatter = ColoredConsoleFormatter()
        record = logging.LogRecord(
            name="engine",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Trade executed",
            args=None,
            exc_info=None,
        )
        record.trade_id = "t-002"  # type: ignore[attr-defined]
        record.symbol = "ETH-USDT"  # type: ignore[attr-defined]

        output = formatter.format(record)
        assert "trade_id=t-002" in output
        assert "symbol=ETH-USDT" in output


class TestSetupLogging:
    """Verify setup_logging configures handlers correctly."""

    def test_creates_log_directory(self, tmp_path: Any) -> None:
        log_dir = str(tmp_path / "test_logs")
        setup_logging(log_dir=log_dir)
        assert os.path.isdir(log_dir)
        # Clean up root handlers
        logging.getLogger().handlers.clear()

    def test_file_handler_writes_json(self, tmp_path: Any) -> None:
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir, log_file="test.log")

        logger = logging.getLogger("test_file_write")
        logger.info("File log test")

        # Flush handlers
        for handler in logging.getLogger().handlers:
            handler.flush()

        log_path = os.path.join(log_dir, "test.log")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read().strip()
        # Should have at least one JSON line
        assert content
        first_line = content.split("\n")[0]
        data = json.loads(first_line)
        assert "timestamp" in data
        assert "level" in data
        assert "component" in data

        logging.getLogger().handlers.clear()

    def test_rotating_file_handler_config(self, tmp_path: Any) -> None:
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir, max_bytes=1024, backup_count=3)

        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if hasattr(h, "maxBytes")
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].maxBytes == 1024
        assert file_handlers[0].backupCount == 3

        logging.getLogger().handlers.clear()


class TestGetLogger:
    """Verify get_logger returns prefixed logger."""

    def test_returns_named_logger(self) -> None:
        logger = get_logger("trading_loop")
        assert logger.name == "trading_loop"
        assert isinstance(logger, logging.Logger)

    def test_different_components_different_loggers(self) -> None:
        l1 = get_logger("risk_manager")
        l2 = get_logger("order_manager")
        assert l1.name != l2.name


class TestTradeLogging:
    """Verify trade executions logged at INFO with context."""

    def test_trade_logged_at_info(self, tmp_path: Any) -> None:
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir, log_file="trade.log")

        logger = get_logger("engine")
        logger.info(
            "Trade executed",
            extra={
                "trade_id": "t-100",
                "symbol": "BTC-USDT",
                "side": "buy",
                "qty": "0.001",
                "price": "42000",
            },
        )

        for handler in logging.getLogger().handlers:
            handler.flush()

        log_path = os.path.join(log_dir, "trade.log")
        with open(log_path) as f:
            lines = f.read().strip().split("\n")

        # Find the trade line
        trade_lines = [l for l in lines if "t-100" in l]
        assert len(trade_lines) >= 1
        data = json.loads(trade_lines[0])
        assert data["level"] == "INFO"
        assert data["trade_id"] == "t-100"

        logging.getLogger().handlers.clear()


class TestRiskEventLogging:
    """Verify risk events logged at WARNING."""

    def test_risk_event_at_warning(self, tmp_path: Any) -> None:
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir, log_file="risk.log")

        logger = get_logger("risk_manager")
        logger.warning("Circuit breaker triggered")

        for handler in logging.getLogger().handlers:
            handler.flush()

        log_path = os.path.join(log_dir, "risk.log")
        with open(log_path) as f:
            lines = f.read().strip().split("\n")

        warning_lines = [l for l in lines if "WARNING" in l]
        assert len(warning_lines) >= 1

        logging.getLogger().handlers.clear()
