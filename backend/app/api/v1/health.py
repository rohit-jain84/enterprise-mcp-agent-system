"""Health check endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter

from app.config import get_settings
from app.db.engine import get_engine
from app.db.redis_client import get_redis
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _check_db() -> str:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return "healthy"
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return f"unhealthy: {exc}"


async def _check_redis() -> str:
    try:
        redis = get_redis()
        await redis.ping()
        return "healthy"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return f"unhealthy: {exc}"


async def _check_mcp(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            if resp.status_code < 400:
                return "healthy"
            return f"unhealthy: status {resp.status_code}"
    except Exception as exc:
        logger.warning("MCP health check failed for %s: %s", url, exc)
        return f"unreachable: {exc}"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check connectivity to DB, Redis, and MCP servers."""
    settings = get_settings()

    db_status = await _check_db()
    redis_status = await _check_redis()

    mcp_servers = {
        "github": await _check_mcp(settings.GITHUB_MCP_URL),
        "project_mgmt": await _check_mcp(settings.PROJECT_MGMT_MCP_URL),
        "calendar": await _check_mcp(settings.CALENDAR_MCP_URL),
    }

    overall = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        mcp_servers=mcp_servers,
        timestamp=datetime.now(UTC),
    )
