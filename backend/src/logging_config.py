"""Structured logging configuration for the OKX Trading Bot."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any


class JsonFormatter(logging.Formatter):
    """Formats log records as JSON with contextual fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields (trade_id, symbol, etc.)
        for key in ("trade_id", "symbol", "side", "qty", "price"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ColoredConsoleFormatter(logging.Formatter):
    """Human-readable colored console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        base = f"{color}{ts} [{record.levelname:<7}]{self.RESET} {record.name}: {record.getMessage()}"

        extras = []
        for key in ("trade_id", "symbol", "side", "qty", "price"):
            val = getattr(record, key, None)
            if val is not None:
                extras.append(f"{key}={val}")
        if extras:
            base += f" ({', '.join(extras)})"

        if record.exc_info and record.exc_info[1]:
            base += "\n" + self.formatException(record.exc_info)

        return base


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "bot.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure the root logger with console and rotating file handlers.

    Args:
        log_dir: Directory for log files.
        log_file: Log file name.
        max_bytes: Max size per log file before rotation (default 10MB).
        backup_count: Number of backup files to keep (default 5).
        console_level: Logging level for console output.
        file_level: Logging level for file output.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    # Console handler — colored human-readable
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredConsoleFormatter())
    root.addHandler(console_handler)

    # File handler — JSON, rotating
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)


def get_logger(component: str) -> logging.Logger:
    """Return a logger prefixed with the component name.

    Args:
        component: The component/module name (e.g. "trading_loop", "risk_manager").

    Returns:
        A configured logging.Logger instance.
    """
    return logging.getLogger(component)
