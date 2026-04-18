"""Session CRUD endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DBSession
from app.models.schemas import (
    MessageResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
)
from app.services.session_service import SessionService

router = APIRouter()


@router.get("", response_model=list[SessionResponse])
async def list_sessions(user: CurrentUser, db: DBSession):
    """Return all sessions for the authenticated user, newest first."""
    svc = SessionService(db)
    sessions = await svc.list_sessions(user_id=user.id)
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, user: CurrentUser, db: DBSession):
    """Create a new chat session."""
    svc = SessionService(db)
    session = await svc.create_session(user_id=user.id, title=body.title)
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Return a session with its messages."""
    svc = SessionService(db)
    session = await svc.get_session_with_messages(session_id=session_id, user_id=user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_session_messages(session_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Return all messages for a session."""
    svc = SessionService(db)
    session = await svc.get_session_with_messages(session_id=session_id, user_id=user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session.messages


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, user: CurrentUser, db: DBSession):
    """Delete a session and its messages."""
    svc = SessionService(db)
    deleted = await svc.delete_session(session_id=session_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
