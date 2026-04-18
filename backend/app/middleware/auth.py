"""JWT verification middleware."""

from __future__ import annotations

import logging

from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings

logger = logging.getLogger(__name__)

# Paths that do not require authentication
PUBLIC_PATHS = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


class JWTMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware that validates the JWT on every request.

    It does NOT block the request if the token is missing -- that is left to
    the ``get_current_user`` dependency so that public endpoints work.
    Instead it attaches ``request.state.user_id`` when a valid token is present
    for downstream logging / auditing purposes.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user_id = None

        # Skip validation for public paths and WebSocket upgrades
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/api/v1/chat/ws"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                settings = get_settings()
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                request.state.user_id = payload.get("sub")
            except JWTError:
                logger.debug("Invalid JWT in middleware (non-blocking)")

        return await call_next(request)
