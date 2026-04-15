"""Write operation tools for the Project Management MCP server (require HITL approval)."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def update_ticket_priority(
        ticket_id: str,
        new_priority: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Update a ticket's priority level. Requires human approval.

        Args:
            ticket_id: The ticket ID (e.g., "PAY-189").
            new_priority: New priority level: P0, P1, P2, P3.
            reason: Optional reason for the priority change.

        Returns:
            Pending approval status with preview of the change.
        """
        error_sim.maybe_error("update_ticket_priority")
        return {
            "status": "pending_approval",
            "action": "update_ticket_priority",
            "preview": {
                "ticket_id": ticket_id,
                "new_priority": new_priority,
                "reason": reason,
            },
        }

    @mcp.tool()
    def update_ticket_assignee(
        ticket_id: str,
        new_assignee: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Reassign a ticket to a different team member. Requires human approval.

        Args:
            ticket_id: The ticket ID (e.g., "PAY-189").
            new_assignee: Username of the new assignee.
            reason: Optional reason for the reassignment.

        Returns:
            Pending approval status with preview of the change.
        """
        error_sim.maybe_error("update_ticket_assignee")
        return {
            "status": "pending_approval",
            "action": "update_ticket_assignee",
            "preview": {
                "ticket_id": ticket_id,
                "new_assignee": new_assignee,
                "reason": reason,
            },
        }

    @mcp.tool()
    def update_ticket_labels(
        ticket_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add or remove labels from a ticket. Requires human approval.

        Args:
            ticket_id: The ticket ID (e.g., "PAY-189").
            add_labels: Labels to add.
            remove_labels: Labels to remove.

        Returns:
            Pending approval status with preview of the change.
        """
        error_sim.maybe_error("update_ticket_labels")
        return {
            "status": "pending_approval",
            "action": "update_ticket_labels",
            "preview": {
                "ticket_id": ticket_id,
                "add_labels": add_labels or [],
                "remove_labels": remove_labels or [],
            },
        }

    @mcp.tool()
    def move_ticket(
        ticket_id: str,
        target_sprint: str | None = None,
        target_status: str | None = None,
    ) -> dict[str, Any]:
        """Move a ticket to a different sprint or change its status. Requires human approval.

        Args:
            ticket_id: The ticket ID (e.g., "PAY-189").
            target_sprint: Sprint ID to move the ticket to (e.g., "PAYMENTS-S25").
            target_status: New status: todo, in_progress, in_review, done, blocked.

        Returns:
            Pending approval status with preview of the change.
        """
        error_sim.maybe_error("move_ticket")
        return {
            "status": "pending_approval",
            "action": "move_ticket",
            "preview": {
                "ticket_id": ticket_id,
                "target_sprint": target_sprint,
                "target_status": target_status,
            },
        }
