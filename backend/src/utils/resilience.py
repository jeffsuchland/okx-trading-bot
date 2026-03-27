"""Reusable resilience decorators and utilities for the OKX Trading Bot."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RateLimitExceeded(Exception):
    """Raised when the rate limiter burst limit is hit and wait=False."""


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator that retries a function on specified exceptions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).
        exceptions: Tuple of exception types to catch and retry on.
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: Exception | None = None
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(
                                "Retry %d/%d for %s after %.1fs delay: %s",
                                attempt + 1,
                                max_retries,
                                func.__name__,
                                delay,
                                e,
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                "All %d retries exhausted for %s: %s",
                                max_retries,
                                func.__name__,
                                e,
                            )
                raise last_exception  # type: ignore[misc]

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs delay: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            e,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries,
                            func.__name__,
                            e,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


class RateLimiter:
    """Token bucket rate limiter for enforcing API rate limits.

    Args:
        max_calls: Maximum number of calls allowed in the period.
        period: Time window in seconds.
    """

    def __init__(self, max_calls: int = 60, period: float = 2.0) -> None:
        self._max_calls = max_calls
        self._period = period
        self._tokens = float(max_calls)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self._max_calls / self._period)
        self._tokens = min(self._max_calls, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self, wait: bool = True) -> None:
        """Acquire a token from the bucket.

        Args:
            wait: If True, sleep until a token is available. If False, raise RateLimitExceeded.
        """
        self._refill()

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return

        if not wait:
            logger.warning(
                "Rate limit exceeded: %d calls / %.1fs",
                self._max_calls,
                self._period,
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self._max_calls} calls per {self._period}s"
            )

        # Wait for a token to become available
        wait_time = (1.0 - self._tokens) * (self._period / self._max_calls)
        logger.info("Rate limiter waiting %.3fs for token", wait_time)
        time.sleep(wait_time)
        self._refill()
        self._tokens -= 1.0

    async def async_acquire(self, wait: bool = True) -> None:
        """Async variant of acquire — use this from async code to avoid blocking the event loop.

        Args:
            wait: If True, sleep until a token is available. If False, raise RateLimitExceeded.
        """
        self._refill()

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return

        if not wait:
            logger.warning(
                "Rate limit exceeded: %d calls / %.1fs",
                self._max_calls,
                self._period,
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self._max_calls} calls per {self._period}s"
            )

        wait_time = (1.0 - self._tokens) * (self._period / self._max_calls)
        logger.info("Rate limiter waiting %.3fs for token", wait_time)
        await asyncio.sleep(wait_time)
        self._refill()
        self._tokens -= 1.0

    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        self._tokens = float(self._max_calls)
        self._last_refill = time.monotonic()


def rate_limiter(max_calls: int = 60, period: float = 2.0) -> Callable[[F], F]:
    """Decorator that enforces rate limits on a function using token bucket.

    Args:
        max_calls: Maximum calls allowed per period.
        period: Time window in seconds.
    """
    limiter = RateLimiter(max_calls=max_calls, period=period)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter.acquire(wait=True)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
