"""Resilience module for error handling and fault tolerance."""

from app.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    circuit_breaker,
)
from app.resilience.retry import (
    retry_async,
    RetryConfig,
    ExponentialBackoff,
)
from app.resilience.fallback import (
    with_fallback,
    FallbackRegistry,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
    "circuit_breaker",
    "retry_async",
    "RetryConfig",
    "ExponentialBackoff",
    "with_fallback",
    "FallbackRegistry",
]
