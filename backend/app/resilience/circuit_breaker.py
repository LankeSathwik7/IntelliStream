"""Circuit breaker pattern implementation for fault tolerance."""

import asyncio
import time
from enum import Enum
from typing import Callable, Dict, Optional, Any
from functools import wraps
from dataclasses import dataclass, field


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation, requests flow through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, name: str, remaining_time: float):
        self.name = name
        self.remaining_time = remaining_time
        super().__init__(f"Circuit breaker '{name}' is open. Retry in {remaining_time:.1f}s")


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 3      # Successes to close from half-open
    timeout: float = 30.0           # Seconds to wait before half-open
    half_open_max_calls: int = 3    # Max calls in half-open state


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    The circuit breaker has three states:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service is failing, requests fail fast
    - HALF_OPEN: Testing if service recovered

    Usage:
        breaker = CircuitBreaker("external-api")

        @breaker
        async def call_external_api():
            return await some_http_call()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0,
        half_open_max_calls: int = 3,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_half_open: Optional[Callable] = None,
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            half_open_max_calls=half_open_max_calls,
        )

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

        # Callbacks
        self._on_open = on_open
        self._on_close = on_close
        self._on_half_open = on_half_open

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats

    def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on state."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time and \
               time.time() - self._last_failure_time >= self.config.timeout:
                self._transition_to_half_open()
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self._half_open_calls < self.config.half_open_max_calls

        return False

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._stats.state_changes += 1

        if self._on_open:
            try:
                self._on_open(self.name)
            except Exception:
                pass

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._success_count = 0
        self._stats.state_changes += 1

        if self._on_half_open:
            try:
                self._on_half_open(self.name)
            except Exception:
                pass

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._stats.state_changes += 1

        if self._on_close:
            try:
                self._on_close(self.name)
            except Exception:
                pass

    def _record_success(self):
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        else:
            # In closed state, reset failure count on success
            self._failure_count = 0

    def _record_failure(self):
        """Record a failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = time.time()
        self._last_failure_time = time.time()
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open returns to open
            self._transition_to_open()
        elif self._failure_count >= self.config.failure_threshold:
            self._transition_to_open()

    async def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        return wrapper

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        async with self._lock:
            if not self._should_allow_request():
                self._stats.rejected_calls += 1
                remaining = self.config.timeout - (time.time() - (self._last_failure_time or 0))
                raise CircuitBreakerOpen(self.name, max(0, remaining))

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._record_success()
            return result

        except Exception as e:
            async with self._lock:
                self._record_failure()
            raise

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        self._transition_to_closed()

    def get_status(self) -> Dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "state_changes": self._stats.state_changes,
            }
        }


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 30.0,
) -> Callable:
    """
    Decorator factory for circuit breaker.

    Usage:
        @circuit_breaker("external-api", failure_threshold=3)
        async def call_api():
            return await httpx.get(url)
    """
    def decorator(func: Callable) -> Callable:
        # Get or create circuit breaker
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
            )

        breaker = _circuit_breakers[name]

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)

        # Attach breaker reference to function
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get circuit breaker by name."""
    return _circuit_breakers.get(name)


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    for breaker in _circuit_breakers.values():
        breaker.reset()
