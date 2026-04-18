"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.db.engine import close_db, init_db
from app.db.redis_client import close_redis, init_redis
from app.middleware.auth import JWTMiddleware
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging_mw import LoggingMiddleware
from app.observability.tracing import configure_tracing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("Starting %s ...", settings.APP_NAME)

    # --- Startup ---
    # Configure LangSmith tracing
    configure_tracing()

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialised")
    except Exception:
        logger.exception("Failed to initialise database")

    # Initialize Redis
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception:
        logger.warning("Redis unavailable -- cost tracking will be degraded", exc_info=True)

    # Log MCP server endpoints
    logger.info(
        "MCP servers: github=%s  project=%s  calendar=%s",
        settings.GITHUB_MCP_URL,
        settings.PROJECT_MGMT_MCP_URL,
        settings.CALENDAR_MCP_URL,
    )

    logger.info("%s ready", settings.APP_NAME)

    yield

    # --- Shutdown ---
    logger.info("Shutting down ...")
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware (order matters: last added runs first) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(JWTMiddleware)
    app.add_middleware(LoggingMiddleware)

    # --- Error handlers ---
    register_error_handlers(app)

    # --- Routes ---
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
