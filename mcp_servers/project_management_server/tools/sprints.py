"""Sprint tools for the Project Management MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_sprints(
        project: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        """List sprints, optionally filtered by project or state.

        Args:
            project: Filter by project key (e.g., "PAYMENTS", "CHECKOUT").
            state: Filter by state: active, completed, planned.

        Returns:
            List of sprints matching the filters.
        """
        error_sim.maybe_error("list_sprints")
        sprints = server.load_data("sprints.json")

        results = sprints
        if project:
            results = [s for s in results if s["project"] == project]
        if state:
            results = [s for s in results if s["state"] == state]

        summaries = []
        for sprint in results:
            summaries.append({
                "id": sprint["id"],
                "name": sprint["name"],
                "project": sprint["project"],
                "state": sprint["state"],
                "start_date": sprint["start_date"],
                "end_date": sprint["end_date"],
                "goal": sprint["goal"],
                "committed_points": sprint["committed_points"],
                "completed_points": sprint["completed_points"],
                "ticket_count": len(sprint.get("tickets", [])),
            })

        return {"total_count": len(summaries), "sprints": summaries}

    @mcp.tool()
    def get_sprint_details(sprint_id: str) -> dict[str, Any]:
        """Get full details of a sprint including ticket breakdown.

        Args:
            sprint_id: The sprint ID (e.g., "PAYMENTS-S24").

        Returns:
            Full sprint details with ticket list and progress.
        """
        error_sim.maybe_error("get_sprint_details")
        sprints = server.load_data("sprints.json")
        tickets = server.load_data("tickets.json")

        for sprint in sprints:
            if sprint["id"] == sprint_id:
                # Enrich with ticket details
                sprint_tickets = [
                    t for t in tickets if t.get("sprint") == sprint_id
                ]
                ticket_breakdown = {
                    "todo": [t for t in sprint_tickets if t["status"] == "todo"],
                    "in_progress": [t for t in sprint_tickets if t["status"] == "in_progress"],
                    "in_review": [t for t in sprint_tickets if t["status"] == "in_review"],
                    "done": [t for t in sprint_tickets if t["status"] == "done"],
                    "blocked": [t for t in sprint_tickets if t["status"] == "blocked"],
                }
                # Summarize tickets (just id, title, status, assignee, points)
                for status_key in ticket_breakdown:
                    ticket_breakdown[status_key] = [
                        {
                            "id": t["id"],
                            "title": t["title"],
                            "type": t["type"],
                            "assignee": t.get("assignee"),
                            "story_points": t.get("story_points"),
                            "priority": t["priority"],
                        }
                        for t in ticket_breakdown[status_key]
                    ]

                return {
                    **sprint,
                    "ticket_breakdown": ticket_breakdown,
                }

        return {"error": f"Sprint {sprint_id} not found"}
