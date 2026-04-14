"""PostgresSaver checkpointer setup for LangGraph."""

from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return a shared AsyncPostgresSaver backed by a connection pool.

    The pool and checkpointer are created once and reused for the lifetime of
    the process.  The connection string is read from ``DATABASE_URL`` in
    settings (converting the ``+asyncpg`` driver hint to a plain
    ``postgresql://`` URI that *psycopg* understands).
    """
    global _pool, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    settings = get_settings()

    # psycopg uses libpq-style URIs -- strip any SQLAlchemy driver suffix.
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    logger.info("Creating AsyncConnectionPool for LangGraph checkpointer")
    _pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=2,
        max_size=10,
        open=False,
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)

    # Create the checkpoint tables if they don't exist yet.
    await _checkpointer.setup()

    logger.info("LangGraph AsyncPostgresSaver is ready")
    return _checkpointer


async def close_checkpointer() -> None:
    """Gracefully close the connection pool on shutdown."""
    global _pool, _checkpointer

    if _pool is not None:
        await _pool.close()
        logger.info("Checkpointer connection pool closed")
    _pool = None
    _checkpointer = None
