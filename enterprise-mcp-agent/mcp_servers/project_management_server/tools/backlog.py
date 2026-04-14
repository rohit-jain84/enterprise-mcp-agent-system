"""Backlog and assignment tools for the Project Management MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def get_backlog(
        project: str | None = None,
    ) -> dict[str, Any]:
        """Get unscheduled backlog tickets (not assigned to any sprint).

        Args:
            project: Filter by project key (e.g., "PAYMENTS").

        Returns:
            List of backlog tickets not assigned to any sprint.
        """
        error_sim.maybe_error("get_backlog")
        tickets = server.load_data("tickets.json")

        backlog = [t for t in tickets if t.get("sprint") is None]
        if project:
            backlog = [t for t in backlog if t["project"] == project]

        summaries = []
        for ticket in backlog:
            summaries.append({
                "id": ticket["id"],
                "project": ticket["project"],
                "title": ticket["title"],
                "type": ticket["type"],
                "priority": ticket["priority"],
                "assignee": ticket.get("assignee"),
                "story_points": ticket.get("story_points"),
                "labels": ticket.get("labels", []),
                "created_at": ticket["created_at"],
            })

        return {"total_count": len(summaries), "backlog_tickets": summaries}

    @mcp.tool()
    def get_assignments(
        username: str | None = None,
    ) -> dict[str, Any]:
        """Get team member workload and current assignments.

        Args:
            username: Filter to a specific team member. If omitted, returns all members.

        Returns:
            Team member workload with assigned tickets.
        """
        error_sim.maybe_error("get_assignments")
        team = server.load_data("team.json")
        tickets = server.load_data("tickets.json")

        members = team
        if username:
            members = [m for m in members if m["username"] == username]

        results = []
        for member in members:
            assigned_tickets = [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "status": t["status"],
                    "priority": t["priority"],
                    "story_points": t.get("story_points"),
                    "sprint": t.get("sprint"),
                }
                for t in tickets
                if t.get("assignee") == member["username"]
                and t["status"] != "done"
            ]

            total_points = sum(t.get("story_points") or 0 for t in assigned_tickets)

            results.append({
                "username": member["username"],
                "full_name": member["full_name"],
                "role": member["role"],
                "capacity_points": member["capacity_points"],
                "current_load_points": total_points,
                "available_capacity": member["capacity_points"] - total_points,
                "active_tickets": assigned_tickets,
                "ticket_count": len(assigned_tickets),
            })

        return {"team_members": results}
