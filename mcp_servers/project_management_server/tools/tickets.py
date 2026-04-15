"""Ticket tools for the Project Management MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_tickets(
        project: str | None = None,
        sprint: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        type: str | None = None,
        priority: str | None = None,
    ) -> dict[str, Any]:
        """List tickets with various filters.

        Args:
            project: Filter by project key (e.g., "PAYMENTS").
            sprint: Filter by sprint ID (e.g., "PAYMENTS-S24").
            status: Filter by status: todo, in_progress, in_review, done, blocked.
            assignee: Filter by assignee username.
            type: Filter by type: bug, feature, improvement, task.
            priority: Filter by priority: P0, P1, P2, P3.

        Returns:
            List of tickets matching the filters.
        """
        error_sim.maybe_error("list_tickets")
        tickets = server.load_data("tickets.json")

        results = tickets
        if project:
            results = [t for t in results if t["project"] == project]
        if sprint:
            results = [t for t in results if t.get("sprint") == sprint]
        if status:
            results = [t for t in results if t["status"] == status]
        if assignee:
            results = [t for t in results if t.get("assignee") == assignee]
        if type:
            results = [t for t in results if t["type"] == type]
        if priority:
            results = [t for t in results if t["priority"] == priority]

        summaries = []
        for ticket in results:
            summaries.append({
                "id": ticket["id"],
                "project": ticket["project"],
                "title": ticket["title"],
                "type": ticket["type"],
                "status": ticket["status"],
                "priority": ticket["priority"],
                "assignee": ticket.get("assignee"),
                "story_points": ticket.get("story_points"),
                "sprint": ticket.get("sprint"),
                "labels": ticket.get("labels", []),
            })

        return {"total_count": len(summaries), "tickets": summaries}

    @mcp.tool()
    def get_ticket_details(ticket_id: str) -> dict[str, Any]:
        """Get full details of a ticket including comments and linked PRs.

        Args:
            ticket_id: The ticket ID (e.g., "PAY-189").

        Returns:
            Full ticket details with comments and linked PRs.
        """
        error_sim.maybe_error("get_ticket_details")
        tickets = server.load_data("tickets.json")

        for ticket in tickets:
            if ticket["id"] == ticket_id:
                return ticket

        return {"error": f"Ticket {ticket_id} not found"}
