"""Issue tools for the GitHub MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_issues(
        repo: str | None = None,
        state: str | None = None,
        labels: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """List issues, optionally filtered by repo, state, labels, or date range.

        Args:
            repo: Filter by repository (e.g., "acme/payments-service").
            state: Filter by state: open, closed.
            labels: Comma-separated labels to filter by.
            since: Start date (ISO format, e.g., "2026-03-25").
            until: End date (ISO format, e.g., "2026-04-08").

        Returns:
            List of issues matching the filters.
        """
        error_sim.maybe_error("list_issues")
        issues = server.load_data("issues.json")

        results = issues
        if repo:
            results = [i for i in results if i["repo"] == repo]
        if state:
            results = [i for i in results if i["state"] == state]
        if labels:
            label_set = {l.strip() for l in labels.split(",")}
            results = [
                i for i in results
                if label_set.intersection(set(i.get("labels", [])))
            ]
        if since:
            results = [i for i in results if i["created_at"] >= since]
        if until:
            results = [i for i in results if i["created_at"] <= until]

        summaries = []
        for issue in results:
            summaries.append({
                "number": issue["number"],
                "repo": issue["repo"],
                "title": issue["title"],
                "state": issue["state"],
                "author": issue["author"],
                "assignees": issue.get("assignees", []),
                "labels": issue.get("labels", []),
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "comment_count": len(issue.get("comments", [])),
            })

        return {"total_count": len(summaries), "issues": summaries}

    @mcp.tool()
    def get_issue_details(repo: str, issue_number: int) -> dict[str, Any]:
        """Get full details of a specific issue including comments.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            issue_number: The issue number.

        Returns:
            Full issue details with comments.
        """
        error_sim.maybe_error("get_issue_details")
        issues = server.load_data("issues.json")

        for issue in issues:
            if issue["repo"] == repo and issue["number"] == issue_number:
                return issue

        return {"error": f"Issue #{issue_number} not found in {repo}"}
