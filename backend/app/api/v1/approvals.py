"""Approval endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DBSession
from app.models.schemas import ApprovalActionRequest, ApprovalResponse
from app.services.approval_service import ApprovalService

router = APIRouter()


@router.get("", response_model=list[ApprovalResponse])
async def list_pending_approvals(user: CurrentUser, db: DBSession):
    """Return all pending approvals visible to the current user."""
    svc = ApprovalService(db)
    approvals = await svc.list_pending(user_id=user.id)
    return approvals


@router.post("/{approval_id}/respond", response_model=ApprovalResponse)
async def respond_to_approval(
    approval_id: uuid.UUID,
    body: ApprovalActionRequest,
    user: CurrentUser,
    db: DBSession,
):
    """Approve or reject a pending tool-call approval."""
    if body.action not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approved' or 'rejected'",
        )

    svc = ApprovalService(db)
    approval = await svc.process_response(
        approval_id=approval_id,
        action=body.action,
        responded_by=user.id,
        reason=body.reason,
    )
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or already processed",
        )
    return approval
