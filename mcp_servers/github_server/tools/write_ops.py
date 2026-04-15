"""Write operation tools for the GitHub MCP server (require HITL approval)."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def create_issue(
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue in a repository. Requires human approval before execution.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            title: Issue title.
            body: Issue body/description in Markdown.
            labels: Optional list of labels to apply.
            assignees: Optional list of usernames to assign.

        Returns:
            Pending approval status with a preview of the issue to be created.
        """
        error_sim.maybe_error("create_issue")
        return {
            "status": "pending_approval",
            "action": "create_issue",
            "preview": {
                "repo": repo,
                "title": title,
                "body": body,
                "labels": labels or [],
                "assignees": assignees or [],
            },
        }

    @mcp.tool()
    def add_comment(
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Add a comment to an issue or pull request. Requires human approval.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            issue_number: The issue or PR number.
            body: Comment body in Markdown.

        Returns:
            Pending approval status with a preview of the comment.
        """
        error_sim.maybe_error("add_comment")
        return {
            "status": "pending_approval",
            "action": "add_comment",
            "preview": {
                "repo": repo,
                "issue_number": issue_number,
                "body": body,
            },
        }

    @mcp.tool()
    def add_labels(
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> dict[str, Any]:
        """Add labels to an issue or pull request. Requires human approval.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            issue_number: The issue or PR number.
            labels: List of label names to add.

        Returns:
            Pending approval status with a preview of the labels to be added.
        """
        error_sim.maybe_error("add_labels")
        return {
            "status": "pending_approval",
            "action": "add_labels",
            "preview": {
                "repo": repo,
                "issue_number": issue_number,
                "labels": labels,
            },
        }
