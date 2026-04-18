"""Request / response logging middleware."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("app.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        logger.info(
            "[%s] %s %s %s started",
            request_id,
            method,
            path,
            client,
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "[%s] %s %s 500 %.1fms (unhandled exception)",
                request_id,
                method,
                path,
                elapsed,
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id

        log_fn = logger.info if response.status_code < 400 else logger.warning
        log_fn(
            "[%s] %s %s %d %.1fms",
            request_id,
            method,
            path,
            response.status_code,
            elapsed,
        )

        return response
