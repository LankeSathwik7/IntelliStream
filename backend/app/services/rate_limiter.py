"""Rate limiting service using Upstash Redis."""

import logging
from typing import Tuple, Optional
from datetime import datetime
from app.services.cache import cache_service
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter using Upstash Redis.

    Implements sliding window rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 30,
        requests_per_hour: int = 500,
        requests_per_day: int = 5000
    ):
        self.limits = {
            "minute": (requests_per_minute, 60),
            "hour": (requests_per_hour, 3600),
            "day": (requests_per_day, 86400),
        }

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "default"
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Args:
            identifier: User ID, IP address, or API key
            endpoint: API endpoint name

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        current_time = int(time.time())
        results = {}

        for window_name, (limit, window_seconds) in self.limits.items():
            key = f"ratelimit:{endpoint}:{identifier}:{window_name}"
            window_start = current_time - window_seconds

            try:
                # Get current count from cache
                count_data = await cache_service.get(key)

                if count_data is None:
                    # First request in this window
                    count = 1
                    await cache_service.set(
                        key,
                        {"count": count, "window_start": current_time},
                        ttl=window_seconds
                    )
                else:
                    # Check if window has expired
                    if count_data.get("window_start", 0) < window_start:
                        # Reset window
                        count = 1
                        await cache_service.set(
                            key,
                            {"count": count, "window_start": current_time},
                            ttl=window_seconds
                        )
                    else:
                        # Increment count
                        count = count_data.get("count", 0) + 1
                        await cache_service.set(
                            key,
                            {"count": count, "window_start": count_data.get("window_start", current_time)},
                            ttl=window_seconds
                        )

                results[window_name] = {
                    "limit": limit,
                    "remaining": max(0, limit - count),
                    "reset": count_data.get("window_start", current_time) + window_seconds if count_data else current_time + window_seconds,
                }

                if count > limit:
                    return False, {
                        "error": f"Rate limit exceeded for {window_name} window",
                        "retry_after": results[window_name]["reset"] - current_time,
                        **results
                    }

            except Exception as e:
                logger.error(f"Rate limit check error: {e}")
                # Allow on error (fail open)
                results[window_name] = {"limit": limit, "remaining": limit, "error": str(e)}

        return True, results

    async def get_usage(self, identifier: str, endpoint: str = "default") -> dict:
        """
        Get current rate limit usage for an identifier.

        Returns:
            Usage stats for all windows
        """
        current_time = int(time.time())
        usage = {}

        for window_name, (limit, window_seconds) in self.limits.items():
            key = f"ratelimit:{endpoint}:{identifier}:{window_name}"

            try:
                count_data = await cache_service.get(key)

                if count_data:
                    usage[window_name] = {
                        "limit": limit,
                        "used": count_data.get("count", 0),
                        "remaining": max(0, limit - count_data.get("count", 0)),
                        "reset_at": datetime.fromtimestamp(
                            count_data.get("window_start", current_time) + window_seconds
                        ).isoformat(),
                    }
                else:
                    usage[window_name] = {
                        "limit": limit,
                        "used": 0,
                        "remaining": limit,
                        "reset_at": None,
                    }

            except Exception as e:
                usage[window_name] = {"error": str(e)}

        return usage

    async def reset_limits(self, identifier: str, endpoint: str = "default") -> bool:
        """Reset rate limits for an identifier (admin function)."""
        try:
            for window_name in self.limits.keys():
                key = f"ratelimit:{endpoint}:{identifier}:{window_name}"
                await cache_service.delete(key)
            return True
        except Exception as e:
            logger.error(f"Reset rate limits error: {e}")
            return False


# Different rate limiters for different use cases
chat_limiter = RateLimiter(
    requests_per_minute=20,  # 20 messages per minute
    requests_per_hour=200,   # 200 messages per hour
    requests_per_day=2000    # 2000 messages per day
)

api_limiter = RateLimiter(
    requests_per_minute=60,   # 60 API calls per minute
    requests_per_hour=1000,   # 1000 API calls per hour
    requests_per_day=10000    # 10000 API calls per day
)

search_limiter = RateLimiter(
    requests_per_minute=30,   # 30 searches per minute
    requests_per_hour=300,    # 300 searches per hour
    requests_per_day=3000     # 3000 searches per day
)
