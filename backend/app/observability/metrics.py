"""Cost and latency metrics collection.

Uses Redis sorted sets for time-series style metric storage.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import redis.asyncio as aioredis

from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)

METRICS_PREFIX = "metrics"
RETENTION_SECONDS = 86400 * 7  # 7 days


class MetricsCollector:
    """Collect and query cost/latency metrics backed by Redis."""

    def __init__(self, redis: aioredis.Redis | None = None) -> None:
        self._redis = redis

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    # ---- Recording ----

    async def record_latency(
        self,
        operation: str,
        latency_ms: float,
        labels: dict | None = None,
    ) -> None:
        """Record a latency measurement."""
        now = time.time()
        key = f"{METRICS_PREFIX}:latency:{operation}"
        entry = json.dumps(
            {
                "latency_ms": round(latency_ms, 2),
                "labels": labels or {},
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        pipe = self.redis.pipeline()
        pipe.zadd(key, {entry: now})
        pipe.expire(key, RETENTION_SECONDS)
        # Trim entries older than retention
        pipe.zremrangebyscore(key, 0, now - RETENTION_SECONDS)
        await pipe.execute()

    async def record_cost(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        cost: float,
        tokens: int,
        model: str = "default",
    ) -> None:
        """Record a cost event."""
        now = time.time()
        key = f"{METRICS_PREFIX}:cost:{user_id}"
        entry = json.dumps(
            {
                "session_id": str(session_id),
                "cost": cost,
                "tokens": tokens,
                "model": model,
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        pipe = self.redis.pipeline()
        pipe.zadd(key, {entry: now})
        pipe.expire(key, RETENTION_SECONDS)
        pipe.zremrangebyscore(key, 0, now - RETENTION_SECONDS)
        await pipe.execute()

    # ---- Querying ----

    async def get_latency_stats(self, operation: str, window_seconds: int = 3600) -> dict:
        """Return min/max/avg/p95 latency for an operation over a time window."""
        key = f"{METRICS_PREFIX}:latency:{operation}"
        now = time.time()
        entries = await self.redis.zrangebyscore(key, now - window_seconds, now)

        if not entries:
            return {"count": 0, "min_ms": 0, "max_ms": 0, "avg_ms": 0, "p95_ms": 0}

        latencies = sorted(json.loads(e)["latency_ms"] for e in entries)
        count = len(latencies)
        p95_idx = int(count * 0.95) - 1
        return {
            "count": count,
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "avg_ms": round(sum(latencies) / count, 2),
            "p95_ms": round(latencies[max(0, p95_idx)], 2),
        }

    async def get_cost_summary(self, user_id: uuid.UUID, window_seconds: int = 86400) -> dict:
        """Return total cost and token usage for a user over a time window."""
        key = f"{METRICS_PREFIX}:cost:{user_id}"
        now = time.time()
        entries = await self.redis.zrangebyscore(key, now - window_seconds, now)

        total_cost = 0.0
        total_tokens = 0
        for raw in entries:
            entry = json.loads(raw)
            total_cost += entry["cost"]
            total_tokens += entry["tokens"]

        return {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "event_count": len(entries),
        }


@asynccontextmanager
async def track_latency(
    collector: MetricsCollector, operation: str, labels: dict | None = None
) -> AsyncGenerator[None, None]:
    """Context manager that measures and records elapsed time."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            await collector.record_latency(operation, elapsed_ms, labels)
        except Exception:
            logger.warning("Failed to record latency metric", exc_info=True)
