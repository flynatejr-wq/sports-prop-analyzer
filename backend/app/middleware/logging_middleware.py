"""
Structured request/response logging middleware.
Logs method, path, status code, duration, and client IP.
"""
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("propedge.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with timing and adds X-Request-ID header."""

    SKIP_PATHS = {"/health", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Attach request ID for downstream use
        request.state.request_id = request_id

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )

        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s %d %.1fms ip=%s id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            ip,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response
