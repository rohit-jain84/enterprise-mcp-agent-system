"""Meeting notes tools for the Calendar MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def get_meeting_notes(meeting_id: str) -> dict[str, Any]:
        """Get notes from a past meeting including discussion points, decisions, and action items.

        Args:
            meeting_id: The meeting ID (e.g., "MTG-001").

        Returns:
            Meeting notes with discussion points, decisions, and action items.
        """
        error_sim.maybe_error("get_meeting_notes")
        notes = server.load_data("meeting_notes.json")

        for note in notes:
            if note["meeting_id"] == meeting_id:
                return note

        return {"error": f"No notes found for meeting {meeting_id}"}
