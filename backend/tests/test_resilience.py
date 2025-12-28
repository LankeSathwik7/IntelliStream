"""Tests for resilience modules (circuit breaker, retry, fallback)."""

import pytest
import asyncio
from unittest.mock import AsyncMock


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    def test_circuit_starts_closed(self):
        """Test circuit breaker starts in closed state."""
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test", failure_threshold=3)

        async def failing_func():
            raise Exception("Test error")

        # Trigger failures
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_rejects_when_open(self):
        """Test open circuit rejects calls."""
        from app.resilience.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerOpen,
            CircuitState
        )

        breaker = CircuitBreaker("test", failure_threshold=1, timeout=60)

        async def failing_func():
            raise Exception("Test error")

        # Open the circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)

        # Should reject
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success(self):
        """Test circuit closes after successful calls in half-open."""
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test", failure_threshold=1, success_threshold=1, timeout=0.01)

        async def failing_func():
            raise Exception("Test error")

        async def success_func():
            return "success"

        # Open circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.02)

        # Should succeed and close
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_get_status(self):
        """Test status reporting."""
        from app.resilience.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker("test-status")
        status = breaker.get_status()

        assert status["name"] == "test-status"
        assert status["state"] == "closed"
        assert "stats" in status

    def test_manual_reset(self):
        """Test manual circuit reset."""
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test")
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 10

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0


class TestRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_first_try(self):
        """Test no retry needed on success."""
        from app.resilience.retry import retry_async

        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(success_func)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failure(self):
        """Test retry succeeds after initial failure."""
        from app.resilience.retry import retry_async, RetryConfig

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = await retry_async(flaky_func, config=config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhaustion raises last error."""
        from app.resilience.retry import retry_async, RetryConfig

        async def always_fail():
            raise Exception("Permanent error")

        config = RetryConfig(max_retries=2, base_delay=0.01)

        with pytest.raises(Exception) as exc:
            await retry_async(always_fail, config=config)

        assert "Permanent error" in str(exc.value)

    @pytest.mark.asyncio
    async def test_retry_callback(self):
        """Test retry callback is called."""
        from app.resilience.retry import retry_async, RetryConfig

        retries = []

        def on_retry(attempt, error, delay):
            retries.append({"attempt": attempt, "error": str(error)})

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Error")
            return "ok"

        config = RetryConfig(max_retries=3, base_delay=0.01)
        await retry_async(flaky_func, config=config, on_retry=on_retry)

        assert len(retries) == 1
        assert retries[0]["attempt"] == 0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        from app.resilience.retry import ExponentialBackoff

        backoff = ExponentialBackoff(base_delay=1.0, max_delay=60.0, jitter=False)

        delay_0 = backoff.get_delay(0)
        delay_1 = backoff.get_delay(1)
        delay_2 = backoff.get_delay(2)

        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0

    def test_exponential_backoff_max(self):
        """Test backoff respects max delay."""
        from app.resilience.retry import ExponentialBackoff

        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0, jitter=False)

        delay = backoff.get_delay(10)  # Would be 1024 without max

        assert delay <= 10.0


class TestFallback:
    """Tests for fallback patterns."""

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Test fallback is used on error."""
        from app.resilience.fallback import with_fallback

        @with_fallback(fallback_value="fallback")
        async def failing_func():
            raise Exception("Error")

        result = await failing_func()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_not_used_on_success(self):
        """Test fallback not used when primary succeeds."""
        from app.resilience.fallback import with_fallback

        @with_fallback(fallback_value="fallback")
        async def success_func():
            return "primary"

        result = await success_func()
        assert result == "primary"

    @pytest.mark.asyncio
    async def test_fallback_with_function(self):
        """Test fallback function is called."""
        from app.resilience.fallback import with_fallback

        async def fallback_fn():
            return "from fallback function"

        @with_fallback(fallback=fallback_fn)
        async def failing_func():
            raise Exception("Error")

        result = await failing_func()
        assert result == "from fallback function"

    @pytest.mark.asyncio
    async def test_fallback_with_timeout(self):
        """Test fallback on timeout."""
        from app.resilience.fallback import with_fallback

        @with_fallback(fallback_value="timeout fallback", timeout=0.01)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "too slow"

        result = await slow_func()
        assert result == "timeout fallback"

    def test_fallback_registry(self):
        """Test fallback registry."""
        from app.resilience.fallback import FallbackRegistry

        registry = FallbackRegistry()

        async def fallback():
            return "registered"

        registry.register("test", fallback)
        assert registry.get("test") is fallback

    def test_cached_fallback(self):
        """Test cached fallback."""
        from app.resilience.fallback import CachedFallback

        cache = CachedFallback()

        # Cache a value
        cache.cache("test_func", (), {}, "cached_value")

        # Retrieve it
        result = cache.get("test_func", (), {})
        assert result == "cached_value"

    def test_cached_fallback_miss(self):
        """Test cached fallback returns None on miss."""
        from app.resilience.fallback import CachedFallback

        cache = CachedFallback()
        result = cache.get("nonexistent", (), {})
        assert result is None


class TestGracefulDegradation:
    """Tests for graceful degradation."""

    @pytest.mark.asyncio
    async def test_degradation_chain(self):
        """Test degradation chain execution."""
        from app.resilience.fallback import GracefulDegradation

        degradation = GracefulDegradation()

        async def primary():
            raise Exception("Primary failed")

        async def secondary():
            return "secondary succeeded"

        degradation.register_chain("test", [
            (primary, "Primary handler"),
            (secondary, "Secondary handler"),
        ])

        result = await degradation.execute("test")
        assert result == "secondary succeeded"

    @pytest.mark.asyncio
    async def test_degradation_first_succeeds(self):
        """Test degradation uses first successful handler."""
        from app.resilience.fallback import GracefulDegradation

        degradation = GracefulDegradation()

        async def primary():
            return "primary succeeded"

        async def secondary():
            return "secondary"

        degradation.register_chain("test", [
            (primary, "Primary"),
            (secondary, "Secondary"),
        ])

        result = await degradation.execute("test")
        assert result == "primary succeeded"
