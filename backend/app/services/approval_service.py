"""Approval service -- create, query, and resolve pending approvals."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import manager
from app.models.database import Approval, Session
from app.models.enums import ApprovalStatus

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_MINUTES = 15


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_approval(
        self,
        session_id: uuid.UUID,
        tool_name: str,
        tool_args: dict,
        reason: str = "",
        expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
    ) -> Approval:
        """Create a new pending approval and broadcast via WebSocket."""
        approval = Approval(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            reason=reason,
            status=ApprovalStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(minutes=expiry_minutes),
        )
        self._db.add(approval)
        await self._db.flush()
        await self._db.refresh(approval)

        # Notify connected WebSocket clients
        await manager.broadcast_to_session(
            session_id,
            {
                "type": "approval_request",
                "payload": {
                    "approval_id": str(approval.id),
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "reason": reason,
                    "expires_at": approval.expires_at.isoformat(),
                },
            },
        )

        logger.info("Approval %s created for tool %s in session %s", approval.id, tool_name, session_id)
        return approval

    async def list_pending(self, user_id: uuid.UUID) -> list[Approval]:
        """Return all pending, non-expired approvals for sessions owned by the user."""
        now = datetime.now(UTC)
        result = await self._db.execute(
            select(Approval)
            .join(Session, Approval.session_id == Session.id)
            .where(
                Session.user_id == user_id,
                Approval.status == ApprovalStatus.PENDING,
                Approval.expires_at > now,
            )
            .order_by(Approval.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_approval(self, approval_id: uuid.UUID) -> Approval | None:
        result = await self._db.execute(select(Approval).where(Approval.id == approval_id))
        return result.scalar_one_or_none()

    async def process_response(
        self,
        approval_id: uuid.UUID,
        action: str,
        responded_by: uuid.UUID | None = None,
        reason: str = "",
    ) -> Approval | None:
        """Approve or reject a pending approval."""
        approval = await self.get_approval(approval_id)
        if approval is None:
            return None

        # Check if already processed
        if approval.status != ApprovalStatus.PENDING:
            logger.warning("Approval %s already has status %s", approval_id, approval.status)
            return None

        # Check expiry
        if approval.expires_at < datetime.now(UTC):
            approval.status = ApprovalStatus.EXPIRED
            await self._db.flush()
            logger.warning("Approval %s has expired", approval_id)
            return None

        approval.status = action  # "approved" or "rejected"
        approval.responded_by = responded_by
        approval.responded_at = datetime.now(UTC)
        if reason:
            approval.reason = reason
        await self._db.flush()
        await self._db.refresh(approval)

        # Notify via WebSocket
        await manager.broadcast_to_session(
            approval.session_id,
            {
                "type": "tool_result",
                "payload": {
                    "approval_id": str(approval.id),
                    "status": approval.status,
                    "tool_name": approval.tool_name,
                },
            },
        )

        logger.info("Approval %s resolved as %s", approval_id, action)
        return approval

    async def expire_stale_approvals(self) -> int:
        """Mark all expired approvals. Returns count of newly expired."""
        now = datetime.now(UTC)
        result = await self._db.execute(
            select(Approval).where(
                Approval.status == ApprovalStatus.PENDING,
                Approval.expires_at <= now,
            )
        )
        stale = result.scalars().all()
        for a in stale:
            a.status = ApprovalStatus.EXPIRED
        await self._db.flush()
        return len(stale)
