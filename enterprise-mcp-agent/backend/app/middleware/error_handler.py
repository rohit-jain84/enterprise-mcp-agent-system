"""Global exception handler returning consistent JSON errors."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "errors": errors,
                "error_code": "VALIDATION_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
