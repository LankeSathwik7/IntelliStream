"""Rate limiting middleware with advanced features."""

import time
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.cache import cache_service
from app.security.rbac import get_role_from_user, get_rate_limits_for_user, Role


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, handling proxies.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for forwarded headers (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with role-based limits.

    Features:
    - Per-user and per-IP rate limiting
    - Role-based limit tiers
    - Sliding window algorithm
    - Rate limit headers in response
    """

    # Endpoints to skip rate limiting
    SKIP_ENDPOINTS = {"/health", "/health/live", "/health/ready", "/", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, default_limit: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""

        # Skip rate limiting for certain endpoints
        if request.url.path in self.SKIP_ENDPOINTS:
            return await call_next(request)

        # Get client identifier
        client_ip = get_client_ip(request)

        # Try to get user from auth header
        user = await self._get_user_from_request(request)
        identifier = user.get("id") if user and user.get("id") else client_ip

        # Get role-based limits
        limits = get_rate_limits_for_user(user)
        limit = limits.get("requests_per_minute", self.default_limit)

        # Check rate limit
        allowed, info = await self._check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            limit=limit,
            window=self.window_seconds
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "limit": limit,
                    "remaining": 0
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info.get("reset", int(time.time()) + 60))
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = info.get("remaining", limit - 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(info.get("reset", int(time.time()) + self.window_seconds))

        return response

    async def _get_user_from_request(self, request: Request) -> Optional[dict]:
        """Extract user from request auth header."""
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            from app.services.auth import auth_service
            return await auth_service.verify_token(token)
        except Exception:
            return None

    async def _check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> tuple:
        """
        Check rate limit using sliding window.

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        current_time = int(time.time())
        key = f"ratelimit:{endpoint}:{identifier}"

        try:
            # Get current window data
            data = await cache_service.get(key)

            if data is None:
                # First request in window
                await cache_service.set(
                    key,
                    {"count": 1, "window_start": current_time},
                    ttl=window
                )
                return True, {"remaining": limit - 1, "reset": current_time + window}

            window_start = data.get("window_start", current_time)
            count = data.get("count", 0)

            # Check if window has expired
            if current_time - window_start >= window:
                # Reset window
                await cache_service.set(
                    key,
                    {"count": 1, "window_start": current_time},
                    ttl=window
                )
                return True, {"remaining": limit - 1, "reset": current_time + window}

            # Increment count
            new_count = count + 1

            if new_count > limit:
                retry_after = window - (current_time - window_start)
                return False, {
                    "remaining": 0,
                    "retry_after": retry_after,
                    "reset": window_start + window
                }

            # Update count
            await cache_service.set(
                key,
                {"count": new_count, "window_start": window_start},
                ttl=window - (current_time - window_start)
            )

            return True, {
                "remaining": limit - new_count,
                "reset": window_start + window
            }

        except Exception as e:
            # Fail open on errors
            print(f"Rate limit check error: {e}")
            return True, {"remaining": limit, "reset": current_time + window}


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on system load.
    """

    def __init__(self, base_limit: int = 30):
        self.base_limit = base_limit
        self.current_multiplier = 1.0

    async def get_adjusted_limit(self, user: Optional[dict] = None) -> int:
        """
        Get rate limit adjusted for current system conditions.

        Args:
            user: Optional user data

        Returns:
            Adjusted rate limit
        """
        base = get_rate_limits_for_user(user).get("requests_per_minute", self.base_limit)

        # Could integrate with monitoring to adjust based on load
        # For now, return base limit
        return int(base * self.current_multiplier)

    def adjust_for_load(self, load_factor: float):
        """
        Adjust rate limits based on system load.

        Args:
            load_factor: 0.0 to 1.0, higher = more load
        """
        if load_factor > 0.8:
            self.current_multiplier = 0.5  # Reduce to 50%
        elif load_factor > 0.6:
            self.current_multiplier = 0.75  # Reduce to 75%
        else:
            self.current_multiplier = 1.0  # Normal limits


# Global adaptive limiter
adaptive_limiter = AdaptiveRateLimiter()
