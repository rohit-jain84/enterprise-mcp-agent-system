"""Commit tools for the GitHub MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_commits(
        repo: str | None = None,
        branch: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """List recent commits, optionally filtered by repo, branch, author, or date range.

        Args:
            repo: Filter by repository (e.g., "acme/payments-service").
            branch: Filter by branch name.
            author: Filter by author username.
            since: Start date (ISO format, e.g., "2026-03-25").
            until: End date (ISO format, e.g., "2026-04-08").

        Returns:
            List of commits matching the filters.
        """
        error_sim.maybe_error("list_commits")
        commits = server.load_data("commits.json")

        results = commits
        if repo:
            results = [c for c in results if c["repo"] == repo]
        if branch:
            results = [c for c in results if c["branch"] == branch]
        if author:
            results = [c for c in results if c["author"] == author]
        if since:
            results = [c for c in results if c["timestamp"] >= since]
        if until:
            results = [c for c in results if c["timestamp"] <= until]

        return {"total_count": len(results), "commits": results}
