"""Meeting tools for the Calendar MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_meetings(
        start_date: str | None = None,
        end_date: str | None = None,
        attendee: str | None = None,
    ) -> dict[str, Any]:
        """List meetings, optionally filtered by date range or attendee.

        Args:
            start_date: Start date filter (ISO format, e.g., "2026-04-07").
            end_date: End date filter (ISO format, e.g., "2026-04-11").
            attendee: Filter by attendee username.

        Returns:
            List of meetings matching the filters.
        """
        error_sim.maybe_error("list_meetings")
        meetings = server.load_data("meetings.json")

        results = meetings
        if start_date:
            results = [m for m in results if m["date"] >= start_date]
        if end_date:
            results = [m for m in results if m["date"] <= end_date]
        if attendee:
            results = [
                m for m in results
                if any(a["username"] == attendee for a in m.get("attendees", []))
            ]

        summaries = []
        for meeting in results:
            summaries.append({
                "id": meeting["id"],
                "title": meeting["title"],
                "meeting_type": meeting["meeting_type"],
                "date": meeting["date"],
                "start_time": meeting["start_time"],
                "end_time": meeting["end_time"],
                "organizer": meeting["organizer"],
                "attendee_count": len(meeting.get("attendees", [])),
                "recurring": meeting.get("recurring", False),
            })

        return {"total_count": len(summaries), "meetings": summaries}

    @mcp.tool()
    def get_meeting_details(meeting_id: str) -> dict[str, Any]:
        """Get full details of a specific meeting.

        Args:
            meeting_id: The meeting ID (e.g., "MTG-001").

        Returns:
            Full meeting details including attendees and description.
        """
        error_sim.maybe_error("get_meeting_details")
        meetings = server.load_data("meetings.json")

        for meeting in meetings:
            if meeting["id"] == meeting_id:
                return meeting

        return {"error": f"Meeting {meeting_id} not found"}

    @mcp.tool()
    def get_attendees(meeting_id: str) -> dict[str, Any]:
        """Get the attendee list for a specific meeting.

        Args:
            meeting_id: The meeting ID (e.g., "MTG-001").

        Returns:
            List of attendees with their response status.
        """
        error_sim.maybe_error("get_attendees")
        meetings = server.load_data("meetings.json")

        for meeting in meetings:
            if meeting["id"] == meeting_id:
                return {
                    "meeting_id": meeting_id,
                    "title": meeting["title"],
                    "attendees": meeting.get("attendees", []),
                }

        return {"error": f"Meeting {meeting_id} not found"}
