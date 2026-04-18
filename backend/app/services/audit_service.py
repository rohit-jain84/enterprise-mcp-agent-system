"""Audit logging service."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.models.enums import AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        user_id: uuid.UUID,
        action: AuditAction | str,
        session_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        """Write an audit log entry."""
        action_str = action.value if isinstance(action, AuditAction) else action
        entry = AuditLog(
            user_id=user_id,
            session_id=session_id,
            action=action_str,
            details=details,
        )
        self._db.add(entry)
        await self._db.flush()
        await self._db.refresh(entry)
        logger.info(
            "Audit: user=%s action=%s session=%s",
            user_id,
            action_str,
            session_id,
        )
        return entry

    async def log_tool_call(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        tool_name: str,
        tool_args: dict,
        result: str | None = None,
    ) -> AuditLog:
        return await self.log(
            user_id=user_id,
            action=AuditAction.TOOL_CALL,
            session_id=session_id,
            details={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "result_preview": (result[:500] if result else None),
            },
        )

    async def log_approval(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        approval_id: uuid.UUID,
        action: str,
        tool_name: str,
    ) -> AuditLog:
        audit_action = AuditAction.APPROVAL_GRANTED if action == "approved" else AuditAction.APPROVAL_REJECTED
        return await self.log(
            user_id=user_id,
            action=audit_action,
            session_id=session_id,
            details={
                "approval_id": str(approval_id),
                "tool_name": tool_name,
            },
        )

    async def log_guardrail(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        rule: str,
        message_preview: str,
    ) -> AuditLog:
        return await self.log(
            user_id=user_id,
            action=AuditAction.GUARDRAIL_TRIGGERED,
            session_id=session_id,
            details={
                "rule": rule,
                "message_preview": message_preview[:200],
            },
        )
