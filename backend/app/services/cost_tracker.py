"""Token and cost tracking using Redis for real-time accumulation."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis

from app.config import get_settings
from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)

# OpenAI pricing (per 1M tokens) -- adjust as needed
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "default": {"input": 2.50, "output": 10.00},
}


@dataclass
class UsageRecord:
    input_tokens: int
    output_tokens: int
    model: str
    cost: float
    timestamp: str


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "default") -> float:
    """Calculate dollar cost from token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class CostTracker:
    """Track per-message and per-session costs using Redis."""

    def __init__(self, redis: aioredis.Redis | None = None) -> None:
        self._redis = redis

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    def _session_key(self, session_id: uuid.UUID) -> str:
        return f"cost:session:{session_id}"

    def _user_key(self, user_id: uuid.UUID) -> str:
        return f"cost:user:{user_id}"

    def _user_daily_key(self, user_id: uuid.UUID) -> str:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"cost:user:{user_id}:daily:{today}"

    async def record_usage(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
    ) -> UsageRecord:
        """Record a usage event and update running totals."""
        cost = calculate_cost(input_tokens, output_tokens, model)
        now = datetime.now(UTC).isoformat()

        record = UsageRecord(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost=cost,
            timestamp=now,
        )

        pipe = self.redis.pipeline()

        # Increment session totals
        session_key = self._session_key(session_id)
        pipe.hincrbyfloat(session_key, "total_cost", cost)
        pipe.hincrby(session_key, "total_input_tokens", input_tokens)
        pipe.hincrby(session_key, "total_output_tokens", output_tokens)
        pipe.hincrby(session_key, "message_count", 1)
        pipe.expire(session_key, 86400 * 30)  # 30-day TTL

        # Increment user totals
        user_key = self._user_key(user_id)
        pipe.hincrbyfloat(user_key, "total_cost", cost)
        pipe.hincrby(user_key, "total_tokens", input_tokens + output_tokens)
        pipe.expire(user_key, 86400 * 90)  # 90-day TTL

        # Increment user daily totals (for budget enforcement)
        daily_key = self._user_daily_key(user_id)
        pipe.incrbyfloat(daily_key, cost)
        pipe.expire(daily_key, 86400 * 2)  # 2-day TTL (auto-cleanup)

        # Push to session history list
        history_key = f"{session_key}:history"
        pipe.rpush(
            history_key,
            json.dumps(
                {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                    "cost": cost,
                    "timestamp": now,
                }
            ),
        )
        pipe.expire(history_key, 86400 * 30)

        await pipe.execute()

        logger.debug(
            "Recorded usage: session=%s tokens=%d+%d cost=%.6f",
            session_id,
            input_tokens,
            output_tokens,
            cost,
        )
        return record

    async def get_session_totals(self, session_id: uuid.UUID) -> dict:
        """Return accumulated cost and token counts for a session."""
        data = await self.redis.hgetall(self._session_key(session_id))
        return {
            "total_cost": float(data.get("total_cost", 0)),
            "total_input_tokens": int(data.get("total_input_tokens", 0)),
            "total_output_tokens": int(data.get("total_output_tokens", 0)),
            "message_count": int(data.get("message_count", 0)),
        }

    async def get_user_totals(self, user_id: uuid.UUID) -> dict:
        """Return accumulated cost and token counts for a user."""
        data = await self.redis.hgetall(self._user_key(user_id))
        return {
            "total_cost": float(data.get("total_cost", 0)),
            "total_tokens": int(data.get("total_tokens", 0)),
        }

    async def get_session_history(self, session_id: uuid.UUID) -> list[dict]:
        """Return the per-message usage history for a session."""
        history_key = f"{self._session_key(session_id)}:history"
        raw_items = await self.redis.lrange(history_key, 0, -1)
        return [json.loads(item) for item in raw_items]

    async def check_budget(self, user_id: uuid.UUID, session_id: uuid.UUID) -> tuple[bool, str]:
        """Check whether the user/session is within budget.

        Returns (allowed, reason).  If allowed is False, reason explains
        which limit was hit and includes current spend vs. limit.
        """
        settings = get_settings()

        # Fetch daily user spend and session spend in one round-trip
        pipe = self.redis.pipeline()
        pipe.get(self._user_daily_key(user_id))
        pipe.hget(self._session_key(session_id), "total_cost")
        daily_raw, session_raw = await pipe.execute()

        daily_spend = float(daily_raw) if daily_raw else 0.0
        session_spend = float(session_raw) if session_raw else 0.0

        if daily_spend >= settings.COST_BUDGET_PER_USER_DAILY:
            return False, (
                f"Daily cost budget exceeded: "
                f"${daily_spend:.4f} spent of ${settings.COST_BUDGET_PER_USER_DAILY:.2f} limit"
            )

        if session_spend >= settings.COST_BUDGET_PER_SESSION:
            return False, (
                f"Session cost budget exceeded: "
                f"${session_spend:.4f} spent of ${settings.COST_BUDGET_PER_SESSION:.2f} limit"
            )

        return True, ""
