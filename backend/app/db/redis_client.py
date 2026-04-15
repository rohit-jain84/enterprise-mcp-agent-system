"""Redis async connection pool."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    """Return the singleton Redis connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
        logger.info("Redis connection pool created")
    return _pool


def get_redis() -> aioredis.Redis:
    """Return a Redis client backed by the shared pool."""
    global _client
    if _client is None:
        _client = aioredis.Redis(connection_pool=get_redis_pool())
    return _client


async def init_redis() -> None:
    """Verify connectivity at startup."""
    client = get_redis()
    await client.ping()
    logger.info("Redis connection verified")


async def close_redis() -> None:
    """Gracefully close the Redis pool."""
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
    logger.info("Redis connection closed")
