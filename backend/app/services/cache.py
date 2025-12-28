"""Upstash Redis caching service."""

import hashlib
import json
from typing import Any, Optional

from upstash_redis import Redis

from app.config import settings


def get_redis_client() -> Redis:
    """Get Redis client."""
    return Redis(
        url=settings.upstash_redis_rest_url,
        token=settings.upstash_redis_rest_token,
    )


class CacheService:
    """Caching operations using Upstash Redis."""

    def __init__(self):
        self._client: Optional[Redis] = None
        self.default_ttl = 3600  # 1 hour

    @property
    def client(self) -> Redis:
        """Lazy-load Redis client."""
        if self._client is None:
            self._client = get_redis_client()
        return self._client

    def _make_key(self, prefix: str, value: str) -> str:
        """Create a cache key with optional hashing for long values."""
        if len(value) > 100:
            hashed = hashlib.md5(value.encode()).hexdigest()
            return f"{prefix}:{hashed}"
        return f"{prefix}:{value}"

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            value = self.client.get(key)
            if value is None:
                return None

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a value in cache."""
        try:
            ttl = ttl or self.default_ttl

            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            self.client.setex(key, ttl, value)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False

    async def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding for text."""
        key = self._make_key("emb", text)
        return await self.get(key)

    async def set_embedding(self, text: str, embedding: list) -> bool:
        """Cache an embedding."""
        key = self._make_key("emb", text)
        return await self.set(key, embedding, ttl=86400)  # 24 hours

    async def get_search_result(self, query: str) -> Optional[dict]:
        """Get cached search result."""
        key = self._make_key("search", query)
        return await self.get(key)

    async def set_search_result(
        self,
        query: str,
        result: dict,
        ttl: int = 1800,  # 30 minutes
    ) -> bool:
        """Cache a search result."""
        key = self._make_key("search", query)
        return await self.set(key, result, ttl=ttl)


# Singleton instance
cache_service = CacheService()
