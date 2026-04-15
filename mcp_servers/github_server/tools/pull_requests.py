"""Pull request tools for the GitHub MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def list_pull_requests(
        repo: str | None = None,
        state: str | None = None,
        author: str | None = None,
    ) -> dict[str, Any]:
        """List pull requests, optionally filtered by repo, state, or author.

        Args:
            repo: Filter by repository (e.g., "acme/payments-service").
            state: Filter by state: open, merged, closed, draft.
            author: Filter by author username.

        Returns:
            List of pull requests matching the filters.
        """
        error_sim.maybe_error("list_pull_requests")
        prs = server.load_data("pull_requests.json")

        results = prs
        if repo:
            results = [pr for pr in results if pr["repo"] == repo]
        if state:
            results = [pr for pr in results if pr["state"] == state]
        if author:
            results = [pr for pr in results if pr["author"] == author]

        # Return summary view (without full diff)
        summaries = []
        for pr in results:
            summaries.append({
                "number": pr["number"],
                "repo": pr["repo"],
                "title": pr["title"],
                "state": pr["state"],
                "author": pr["author"],
                "branch": pr["branch"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "ci_status": pr["ci_status"],
                "labels": pr.get("labels", []),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "changed_files": pr.get("changed_files", 0),
            })

        return {"total_count": len(summaries), "pull_requests": summaries}

    @mcp.tool()
    def get_pr_details(repo: str, pr_number: int) -> dict[str, Any]:
        """Get full details of a specific pull request including reviewers and CI status.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            pr_number: The pull request number.

        Returns:
            Full pull request details.
        """
        error_sim.maybe_error("get_pr_details")
        prs = server.load_data("pull_requests.json")

        for pr in prs:
            if pr["repo"] == repo and pr["number"] == pr_number:
                return pr

        return {"error": f"Pull request #{pr_number} not found in {repo}"}

    @mcp.tool()
    def get_pr_diff(repo: str, pr_number: int) -> dict[str, Any]:
        """Get the unified diff text for a pull request.

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            pr_number: The pull request number.

        Returns:
            Diff text and summary of changes.
        """
        error_sim.maybe_error("get_pr_diff")
        prs = server.load_data("pull_requests.json")

        for pr in prs:
            if pr["repo"] == repo and pr["number"] == pr_number:
                return {
                    "repo": repo,
                    "pr_number": pr_number,
                    "title": pr["title"],
                    "diff_summary": pr.get("diff_summary", "No diff available"),
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                }

        return {"error": f"Pull request #{pr_number} not found in {repo}"}
