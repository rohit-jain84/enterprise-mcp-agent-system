"""Application enumerations."""

from __future__ import annotations

import enum


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class AuditAction(str, enum.Enum):
    TOOL_CALL = "tool_call"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
