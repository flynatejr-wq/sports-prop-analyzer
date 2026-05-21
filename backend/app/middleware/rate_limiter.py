"""
Sliding-window rate limiter middleware using Redis (or in-memory fallback).
Limits requests per IP per minute to prevent abuse.
"""
import logging
import time
from typing import Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory fallback: {ip: [(timestamp, count)]}
_memory_store: Dict[str, list] = {}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limits incoming API requests by client IP.
    Config (via settings):
      RATE_LIMIT_REQUESTS: max requests per window
      RATE_LIMIT_WINDOW:   window size in seconds
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 120,
        window_seconds: int = 60,
        whitelist_paths: Tuple[str, ...] = ("/health", "/docs", "/redoc", "/openapi.json", "/ws"),
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.whitelist_paths = whitelist_paths
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await r.ping()
                self._redis = r
            except Exception:
                pass
        return self._redis

    def _is_whitelisted(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.whitelist_paths)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._is_whitelisted(request.url.path):
            return await call_next(request)

        ip = self._get_client_ip(request)
        allowed, remaining, reset_in = await self._check_rate_limit(ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": reset_in,
                },
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response

    async def _check_rate_limit(self, ip: str) -> Tuple[bool, int, int]:
        """
        Returns (is_allowed, remaining_requests, seconds_until_reset).
        Uses Redis ZADD sliding window if available, memory fallback otherwise.
        """
        r = await self._get_redis()
        now = time.time()
        window_start = now - self.window_seconds
        key = f"rate:{ip}"

        if r:
            try:
                pipe = r.pipeline()
                await pipe.zremrangebyscore(key, 0, window_start)
                await pipe.zcard(key)
                await pipe.zadd(key, {str(now): now})
                await pipe.expire(key, self.window_seconds + 1)
                results = await pipe.execute()
                count = results[1]
                allowed = count < self.requests_per_window
                remaining = max(0, self.requests_per_window - count - 1)
                return allowed, remaining, self.window_seconds
            except Exception:
                pass

        # Memory fallback
        if ip not in _memory_store:
            _memory_store[ip] = []
        timestamps = _memory_store[ip]
        # Prune old entries
        _memory_store[ip] = [t for t in timestamps if t > window_start]
        count = len(_memory_store[ip])
        if count >= self.requests_per_window:
            oldest = min(_memory_store[ip]) if _memory_store[ip] else now
            reset_in = max(1, int(oldest + self.window_seconds - now))
            return False, 0, reset_in
        _memory_store[ip].append(now)
        return True, self.requests_per_window - count - 1, self.window_seconds
