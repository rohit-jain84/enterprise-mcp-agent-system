"""Aggregated v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import approvals, auth, chat, health, mcp_servers, reports, sessions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(mcp_servers.router, prefix="/mcp", tags=["mcp"])
