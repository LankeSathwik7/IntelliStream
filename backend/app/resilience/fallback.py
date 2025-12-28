"""Fallback patterns for graceful degradation."""

import asyncio
import inspect
from typing import Callable, TypeVar, Optional, Dict, Any, Union
from functools import wraps
from dataclasses import dataclass
import time


T = TypeVar('T')


@dataclass
class FallbackResult:
    """Result from fallback execution."""

    value: Any
    source: str  # "primary" or "fallback"
    error: Optional[Exception] = None
    execution_time: float = 0.0


class FallbackRegistry:
    """
    Registry for managing fallback functions.

    Provides a central place to register and retrieve fallback handlers.
    """

    def __init__(self):
        self._fallbacks: Dict[str, Callable] = {}
        self._stats: Dict[str, Dict[str, int]] = {}

    def register(self, name: str, fallback: Callable):
        """Register a fallback function."""
        self._fallbacks[name] = fallback
        self._stats[name] = {"primary_calls": 0, "fallback_calls": 0}

    def get(self, name: str) -> Optional[Callable]:
        """Get a registered fallback."""
        return self._fallbacks.get(name)

    def record_primary(self, name: str):
        """Record successful primary call."""
        if name in self._stats:
            self._stats[name]["primary_calls"] += 1

    def record_fallback(self, name: str):
        """Record fallback call."""
        if name in self._stats:
            self._stats[name]["fallback_calls"] += 1

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get fallback statistics."""
        result = {}
        for name, stats in self._stats.items():
            total = stats["primary_calls"] + stats["fallback_calls"]
            result[name] = {
                **stats,
                "fallback_rate": stats["fallback_calls"] / total if total > 0 else 0
            }
        return result


# Global fallback registry
fallback_registry = FallbackRegistry()


def with_fallback(
    fallback: Optional[Callable] = None,
    fallback_value: Any = None,
    fallback_name: Optional[str] = None,
    timeout: Optional[float] = None,
    log_errors: bool = True,
) -> Callable:
    """
    Decorator to provide fallback behavior on failure.

    Usage:
        @with_fallback(fallback_value="default")
        async def unreliable_function():
            return await some_call()

        # Or with fallback function:
        @with_fallback(fallback=async_fallback_function)
        async def unreliable_function():
            return await some_call()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            func_name = fallback_name or getattr(func, '__name__', str(func))

            try:
                # Apply timeout if specified
                if timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                fallback_registry.record_primary(func_name)
                return result

            except asyncio.TimeoutError as e:
                if log_errors:
                    print(f"Timeout in {func_name}: {timeout}s exceeded")
                return await _execute_fallback(
                    fallback, fallback_value, func_name, e, args, kwargs
                )

            except Exception as e:
                if log_errors:
                    print(f"Error in {func_name}: {e}")
                return await _execute_fallback(
                    fallback, fallback_value, func_name, e, args, kwargs
                )

        return wrapper

    return decorator


async def _execute_fallback(
    fallback: Optional[Callable],
    fallback_value: Any,
    name: str,
    error: Exception,
    args: tuple,
    kwargs: dict
) -> Any:
    """Execute fallback function or return fallback value."""
    fallback_registry.record_fallback(name)

    # Try registered fallback first
    registered = fallback_registry.get(name)
    if registered:
        try:
            if inspect.iscoroutinefunction(registered):
                return await registered(*args, **kwargs)
            return registered(*args, **kwargs)
        except Exception as e:
            print(f"Registered fallback failed for {name}: {e}")

    # Try provided fallback function
    if fallback:
        try:
            if inspect.iscoroutinefunction(fallback):
                return await fallback(*args, **kwargs)
            return fallback(*args, **kwargs)
        except Exception as e:
            print(f"Fallback function failed for {name}: {e}")

    # Return fallback value
    if fallback_value is not None:
        return fallback_value

    # Re-raise original error if no fallback available
    raise error


class CachedFallback:
    """
    Fallback that uses cached values when primary fails.

    Maintains a cache of successful responses to use as fallbacks.
    """

    def __init__(self, max_cache_size: int = 100, cache_ttl: float = 3600):
        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self._max_size = max_cache_size
        self._ttl = cache_ttl

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create cache key from function call."""
        # Simple key - could be more sophisticated
        return f"{func_name}:{hash(str(args) + str(sorted(kwargs.items())))}"

    def _clean_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired = [
            k for k, (v, t) in self._cache.items()
            if current_time - t > self._ttl
        ]
        for k in expired:
            del self._cache[k]

    def cache(self, func_name: str, args: tuple, kwargs: dict, value: Any):
        """Cache a successful result."""
        self._clean_expired()

        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1][1])
            del self._cache[oldest[0]]

        key = self._make_key(func_name, args, kwargs)
        self._cache[key] = (value, time.time())

    def get(self, func_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """Get cached value if available."""
        key = self._make_key(func_name, args, kwargs)

        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        # Check if expired
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None

        return value


# Global cached fallback
cached_fallback = CachedFallback()


def with_cached_fallback(
    timeout: Optional[float] = None,
    cache_ttl: float = 3600,
) -> Callable:
    """
    Decorator that caches successful responses as fallbacks.

    Usage:
        @with_cached_fallback(timeout=5.0)
        async def get_data():
            return await fetch_from_api()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            func_name = getattr(func, '__name__', str(func))

            try:
                if timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                # Cache successful result
                cached_fallback.cache(func_name, args, kwargs, result)
                return result

            except Exception as e:
                # Try to get cached value
                cached = cached_fallback.get(func_name, args, kwargs)

                if cached is not None:
                    print(f"Using cached fallback for {func_name}")
                    return cached

                raise

        return wrapper

    return decorator


class GracefulDegradation:
    """
    Graceful degradation manager for complex fallback chains.

    Supports multiple fallback levels with priority ordering.
    """

    def __init__(self):
        self._chains: Dict[str, list] = {}

    def register_chain(self, name: str, handlers: list):
        """
        Register a fallback chain.

        Args:
            name: Chain name
            handlers: List of (callable, description) tuples in priority order
        """
        self._chains[name] = handlers

    async def execute(self, name: str, *args, **kwargs) -> Any:
        """
        Execute fallback chain until one succeeds.

        Args:
            name: Chain name
            *args, **kwargs: Arguments to pass to handlers

        Returns:
            Result from first successful handler

        Raises:
            Exception: If all handlers fail
        """
        if name not in self._chains:
            raise ValueError(f"Unknown fallback chain: {name}")

        last_error: Optional[Exception] = None

        for handler, description in self._chains[name]:
            try:
                print(f"Trying: {description}")

                if inspect.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)

                return result

            except Exception as e:
                print(f"Failed: {description} - {e}")
                last_error = e
                continue

        if last_error:
            raise last_error

        raise RuntimeError(f"Fallback chain '{name}' has no handlers")


# Global degradation manager
degradation = GracefulDegradation()
