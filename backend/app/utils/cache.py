"""
Redis cache wrapper with JSON serialization and TTL support.
Falls back gracefully to an in-memory dict if Redis is unavailable.
"""
import asyncio
import json
import logging
from typing import Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class _MemoryCache:
    """In-process fallback cache — not shared across workers."""
    def __init__(self):
        self._store: dict = {}
        self._expires: dict = {}

    async def get(self, key: str) -> Optional[Any]:
        import time
        exp = self._expires.get(key)
        if exp and time.time() > exp:
            self._store.pop(key, None)
            self._expires.pop(key, None)
            return None
        val = self._store.get(key)
        if val is None:
            return None
        return json.loads(val)

    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL):
        import time
        self._store[key] = json.dumps(value, default=str)
        self._expires[key] = time.time() + ttl

    async def delete(self, key: str):
        self._store.pop(key, None)
        self._expires.pop(key, None)

    async def flush(self):
        self._store.clear()
        self._expires.clear()


class RedisCache:
    def __init__(self):
        self._redis = None
        self._fallback = _MemoryCache()
        self._connected = False

    async def _get_redis(self):
        if self._redis is None and not self._connected:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.info("Redis connected: %s", settings.REDIS_URL)
            except Exception as exc:
                logger.warning("Redis unavailable (%s) — using memory cache", exc)
                self._redis = None
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        r = await self._get_redis()
        if r:
            try:
                val = await r.get(key)
                return json.loads(val) if val else None
            except Exception:
                pass
        return await self._fallback.get(key)

    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL):
        r = await self._get_redis()
        if r:
            try:
                await r.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception:
                pass
        await self._fallback.set(key, value, ttl)

    async def delete(self, key: str):
        r = await self._get_redis()
        if r:
            try:
                await r.delete(key)
                return
            except Exception:
                pass
        await self._fallback.delete(key)

    async def get_or_set(self, key: str, factory, ttl: int = settings.CACHE_TTL) -> Any:
        """Get from cache; if missing call factory() to populate."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        await self.set(key, value, ttl)
        return value


# Singleton used across the app
cache = RedisCache()
