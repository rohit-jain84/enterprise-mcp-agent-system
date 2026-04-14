"""Report generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DBSession
from app.models.schemas import ReportRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(body: ReportRequest, user: CurrentUser, db: DBSession):
    """Generate a markdown report for the given session."""
    svc = ReportService(db)
    report = await svc.generate(
        session_id=body.session_id,
        user_id=user.id,
        include_tool_calls=body.include_tool_calls,
        include_costs=body.include_costs,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return report
