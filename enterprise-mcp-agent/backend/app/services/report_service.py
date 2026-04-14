"""Report generation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import Message, Session
from app.models.enums import MessageRole
from app.models.schemas import ReportResponse


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def generate(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        include_tool_calls: bool = True,
        include_costs: bool = True,
    ) -> ReportResponse | None:
        """Generate a markdown report for a session."""
        result = await self._db.execute(
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id, Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return None

        lines: list[str] = []
        lines.append(f"# Session Report: {session.title}")
        lines.append("")
        lines.append(f"**Session ID:** `{session.id}`")
        lines.append(f"**Created:** {session.created_at.isoformat()}")
        lines.append(f"**Last Updated:** {session.updated_at.isoformat()}")

        if include_costs:
            lines.append("")
            lines.append("## Cost Summary")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Total Tokens | {session.total_tokens:,} |")
            lines.append(f"| Total Cost | ${session.total_cost:.4f} |")
            lines.append(f"| Messages | {len(session.messages)} |")

        lines.append("")
        lines.append("## Conversation")
        lines.append("")

        for msg in session.messages:
            role_label = msg.role.upper()
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

            lines.append(f"### [{role_label}] {timestamp}")
            lines.append("")

            if msg.role == MessageRole.TOOL and include_tool_calls:
                lines.append("```")
                lines.append(msg.content[:2000])
                lines.append("```")
            else:
                lines.append(msg.content)

            if include_tool_calls and msg.tool_calls:
                lines.append("")
                lines.append("**Tool Calls:**")
                lines.append("```json")
                import json
                lines.append(json.dumps(msg.tool_calls, indent=2)[:3000])
                lines.append("```")

            if include_tool_calls and msg.tool_results:
                lines.append("")
                lines.append("**Tool Results:**")
                lines.append("```json")
                import json
                lines.append(json.dumps(msg.tool_results, indent=2)[:3000])
                lines.append("```")

            if include_costs and (msg.token_count or msg.cost):
                lines.append(f"\n*Tokens: {msg.token_count:,} | Cost: ${msg.cost:.6f}*")

            lines.append("")

        lines.append("---")
        lines.append(f"*Report generated at {datetime.now(timezone.utc).isoformat()}*")

        markdown = "\n".join(lines)

        return ReportResponse(
            session_id=session_id,
            markdown=markdown,
            generated_at=datetime.now(timezone.utc),
        )
