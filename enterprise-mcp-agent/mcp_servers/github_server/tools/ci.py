"""CI status tools for the GitHub MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def get_ci_status(repo: str, ref: str) -> dict[str, Any]:
        """Get CI pipeline status for a given ref (branch name or PR number).

        Args:
            repo: Repository name (e.g., "acme/payments-service").
            ref: Git ref - branch name (e.g., "main") or PR ref (e.g., "pr-247").

        Returns:
            CI pipeline status with individual check details.
        """
        error_sim.maybe_error("get_ci_status")
        statuses = server.load_data("ci_status.json")

        for status in statuses:
            if status["repo"] == repo and status["ref"] == ref:
                return status

        return {"error": f"No CI status found for {ref} in {repo}"}
