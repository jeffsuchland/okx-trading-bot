"""Tests for error handling and resilience patterns."""

from __future__ import annotations

import logging
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.utils.resilience import (
    RateLimitExceeded,
    RateLimiter,
    rate_limiter,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Verify retry_with_backoff decorator."""

    @patch("src.utils.resilience.time.sleep")
    def test_retries_on_exception(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(ValueError,))
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # slept before retry 2 and 3

    @patch("src.utils.resilience.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep: MagicMock) -> None:
        @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(ConnectionError,))
        def always_fails() -> None:
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            always_fails()

        # Delays: 1.0, 2.0, 4.0
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]

    @patch("src.utils.resilience.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep: MagicMock) -> None:
        @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(RuntimeError,))
        def always_fails() -> None:
            raise RuntimeError("permanent")

        with pytest.raises(RuntimeError, match="permanent"):
            always_fails()

    def test_no_retry_on_unmatched_exception(self) -> None:
        @retry_with_backoff(max_retries=3, base_delay=0.1, exceptions=(ValueError,))
        def raises_type_error() -> None:
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raises_type_error()

    @patch("src.utils.resilience.time.sleep")
    def test_succeeds_without_exception(self, mock_sleep: MagicMock) -> None:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def ok_func() -> int:
            return 42

        assert ok_func() == 42
        mock_sleep.assert_not_called()

    @patch("src.utils.resilience.time.sleep")
    def test_logs_retry_attempts(self, mock_sleep: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(ValueError,))
        def flaky() -> str:
            raise ValueError("flaky")

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                flaky()

        assert "Retry 1/2" in caplog.text
        assert "Retry 2/2" in caplog.text

    @patch("src.utils.resilience.time.sleep")
    def test_configurable_exception_types(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(ConnectionError, TimeoutError))
        def multi_error() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("conn")
            if call_count == 2:
                raise TimeoutError("timeout")
            return "ok"

        result = multi_error()
        assert result == "ok"
        assert call_count == 3


class TestRateLimiter:
    """Verify RateLimiter token bucket implementation."""

    def test_allows_calls_within_limit(self) -> None:
        limiter = RateLimiter(max_calls=5, period=1.0)
        for _ in range(5):
            limiter.acquire(wait=False)  # Should not raise

    def test_raises_when_limit_exceeded_no_wait(self) -> None:
        limiter = RateLimiter(max_calls=2, period=1.0)
        limiter.acquire(wait=False)
        limiter.acquire(wait=False)
        with pytest.raises(RateLimitExceeded):
            limiter.acquire(wait=False)

    @patch("src.utils.resilience.time.sleep")
    def test_waits_when_limit_exceeded_wait_true(self, mock_sleep: MagicMock) -> None:
        limiter = RateLimiter(max_calls=1, period=1.0)
        limiter.acquire(wait=False)  # Uses the one token

        # Force refill to give back tokens after sleep
        limiter._tokens = 0.0
        limiter._last_refill = time.monotonic() - 2.0  # pretend 2s passed

        limiter.acquire(wait=True)  # Should succeed after refill

    def test_reset_restores_capacity(self) -> None:
        limiter = RateLimiter(max_calls=2, period=1.0)
        limiter.acquire(wait=False)
        limiter.acquire(wait=False)
        with pytest.raises(RateLimitExceeded):
            limiter.acquire(wait=False)

        limiter.reset()
        limiter.acquire(wait=False)  # Should work after reset

    def test_logs_rate_limit_exceeded(self, caplog: pytest.LogCaptureFixture) -> None:
        limiter = RateLimiter(max_calls=1, period=1.0)
        limiter.acquire(wait=False)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(RateLimitExceeded):
                limiter.acquire(wait=False)

        assert "Rate limit exceeded" in caplog.text


class TestRateLimiterDecorator:
    """Verify the @rate_limiter decorator."""

    def test_decorator_enforces_limit(self) -> None:
        call_count = 0

        @rate_limiter(max_calls=100, period=1.0)
        def api_call() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # Should succeed for many calls with high limit
        for _ in range(10):
            api_call()
        assert call_count == 10
