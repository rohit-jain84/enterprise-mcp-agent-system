"""Pydantic request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ApprovalStatus, MessageRole


# ---------- Auth ----------

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Users ----------

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ---------- Sessions ----------

class SessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    metadata: dict | None = Field(default=None, alias="metadata_")


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    total_tokens: int
    total_cost: float
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = []


# ---------- Messages ----------

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    tool_calls: dict | None = None
    tool_results: dict | None = None
    token_count: int
    cost: float
    created_at: datetime


# ---------- Chat ----------

class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=32_000)


class ChatResponse(BaseModel):
    message_id: uuid.UUID
    session_id: uuid.UUID
    content: str
    tool_calls: list[dict] | None = None
    token_count: int = 0
    cost: float = 0.0


# ---------- Approvals ----------

class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    tool_name: str
    tool_args: dict
    reason: str
    status: str
    responded_by: uuid.UUID | None = None
    responded_at: datetime | None = None
    expires_at: datetime
    created_at: datetime


class ApprovalActionRequest(BaseModel):
    action: ApprovalStatus = Field(
        ..., description="Must be 'approved' or 'rejected'"
    )
    reason: str = Field(default="", max_length=1000)


# ---------- Reports ----------

class ReportRequest(BaseModel):
    session_id: uuid.UUID
    include_tool_calls: bool = True
    include_costs: bool = True


class ReportResponse(BaseModel):
    session_id: uuid.UUID
    markdown: str
    generated_at: datetime


# ---------- Health ----------

class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    mcp_servers: dict[str, str]
    timestamp: datetime


# ---------- WebSocket Messages ----------

class WSMessage(BaseModel):
    """Envelope for WebSocket messages from the client."""
    type: str  # user_message | approval_response
    payload: dict = {}


class WSOutbound(BaseModel):
    """Envelope for WebSocket messages to the client."""
    type: str  # stream_start | stream_chunk | stream_end | tool_call | tool_result | approval_request | error
    payload: dict = {}


# ---------- Error ----------

class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
