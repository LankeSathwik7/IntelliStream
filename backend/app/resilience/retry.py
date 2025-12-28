"""Retry logic with exponential backoff for resilient operations."""

import asyncio
import random
from typing import Callable, TypeVar, Optional, Tuple, Type, Union, List
from functools import wraps
from dataclasses import dataclass
import time


T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay
    exponential_base: float = 2.0
    jitter: bool = True  # Add random jitter to prevent thundering herd
    jitter_factor: float = 0.5  # Jitter as fraction of delay

    # Exceptions to retry on (empty = retry all)
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)

    # Exceptions to never retry
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        KeyboardInterrupt,
        SystemExit,
        ValueError,
        TypeError,
    )


class ExponentialBackoff:
    """
    Exponential backoff calculator with jitter.

    Implements the "decorrelated jitter" algorithm for better distribution.
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.5
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self._last_delay = base_delay

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential delay
        delay = self.base_delay * (self.exponential_base ** attempt)

        # Apply jitter
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)

        # Clamp to max delay
        delay = min(delay, self.max_delay)

        # Ensure positive
        delay = max(0.1, delay)

        self._last_delay = delay
        return delay

    def get_decorrelated_delay(self, attempt: int) -> float:
        """
        Get delay using decorrelated jitter algorithm.

        This provides better distribution than simple exponential.
        """
        if attempt == 0:
            return self.base_delay

        delay = random.uniform(
            self.base_delay,
            self._last_delay * 3
        )
        delay = min(delay, self.max_delay)
        self._last_delay = delay
        return delay


class RetryStats:
    """Statistics for retry operations."""

    def __init__(self):
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.total_retries = 0
        self.total_delay = 0.0

    def record_attempt(self, success: bool, retries: int, delay: float):
        """Record an attempt."""
        self.total_attempts += 1
        self.total_retries += retries
        self.total_delay += delay

        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts

    @property
    def average_retries(self) -> float:
        """Calculate average retries per attempt."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_retries / self.total_attempts


# Global retry stats
_retry_stats: dict = {}


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    **kwargs
) -> T:
    """
    Execute async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments
        config: Retry configuration
        on_retry: Callback called on each retry (attempt, exception, delay)
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    backoff = ExponentialBackoff(
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        exponential_base=config.exponential_base,
        jitter=config.jitter,
        jitter_factor=config.jitter_factor
    )

    last_exception: Optional[Exception] = None
    total_delay = 0.0
    func_name = getattr(func, '__name__', str(func))

    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)

            # Record success
            if func_name in _retry_stats:
                _retry_stats[func_name].record_attempt(True, attempt, total_delay)

            return result

        except config.non_retryable_exceptions as e:
            # Don't retry these
            raise

        except config.retryable_exceptions as e:
            last_exception = e

            # Last attempt, don't retry
            if attempt >= config.max_retries:
                break

            # Calculate delay
            delay = backoff.get_decorrelated_delay(attempt)
            total_delay += delay

            # Call retry callback
            if on_retry:
                try:
                    on_retry(attempt, e, delay)
                except Exception:
                    pass

            # Wait before retry
            await asyncio.sleep(delay)

    # Record failure
    if func_name not in _retry_stats:
        _retry_stats[func_name] = RetryStats()
    _retry_stats[func_name].record_attempt(False, config.max_retries, total_delay)

    # Raise last exception
    if last_exception:
        raise last_exception

    raise RuntimeError("Retry loop completed without result or exception")


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable:
    """
    Decorator factory for retry logic.

    Usage:
        @retry(max_retries=3, base_delay=1.0)
        async def flaky_function():
            return await some_unreliable_call()
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func,
                *args,
                config=config,
                on_retry=on_retry,
                **kwargs
            )

        return wrapper

    return decorator


def retry_with_circuit_breaker(
    circuit_breaker_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Callable:
    """
    Combine retry logic with circuit breaker.

    Usage:
        @retry_with_circuit_breaker("external-api", max_retries=3)
        async def call_api():
            return await httpx.get(url)
    """
    from app.resilience.circuit_breaker import circuit_breaker as cb

    def decorator(func: Callable) -> Callable:
        # Apply circuit breaker first, then retry
        @retry(max_retries=max_retries, base_delay=base_delay)
        @cb(circuit_breaker_name)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_retry_stats(func_name: str) -> Optional[RetryStats]:
    """Get retry statistics for a function."""
    return _retry_stats.get(func_name)


def get_all_retry_stats() -> dict:
    """Get all retry statistics."""
    return {
        name: {
            "total_attempts": stats.total_attempts,
            "successful_attempts": stats.successful_attempts,
            "failed_attempts": stats.failed_attempts,
            "success_rate": stats.success_rate,
            "average_retries": stats.average_retries,
            "total_delay": stats.total_delay,
        }
        for name, stats in _retry_stats.items()
    }
