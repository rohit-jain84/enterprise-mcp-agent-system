"""Session CRUD service."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import Message, Session


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_sessions(self, user_id: uuid.UUID) -> list[Session]:
        """Return all sessions for a user, ordered by most recently updated."""
        result = await self._db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_session(self, user_id: uuid.UUID, title: str = "New Chat") -> Session:
        """Create and persist a new session."""
        session = Session(user_id=user_id, title=title)
        self._db.add(session)
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> Session | None:
        """Return a session if it belongs to the user."""
        result = await self._db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_session_with_messages(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Session | None:
        """Return a session eagerly loaded with its messages."""
        result = await self._db.execute(
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id, Session.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a session; return True if it existed."""
        result = await self._db.execute(
            delete(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        return result.rowcount > 0

    async def update_session_costs(
        self, session_id: uuid.UUID, tokens: int, cost: float
    ) -> None:
        """Increment token and cost counters on a session."""
        result = await self._db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.total_tokens += tokens
            session.total_cost += cost
            await self._db.flush()

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        tool_calls: dict | None = None,
        tool_results: dict | None = None,
        token_count: int = 0,
        cost: float = 0.0,
    ) -> Message:
        """Append a message to a session."""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            token_count=token_count,
            cost=cost,
        )
        self._db.add(message)
        await self._db.flush()
        await self._db.refresh(message)
        return message
