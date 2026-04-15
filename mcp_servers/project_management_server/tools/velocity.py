"""Velocity tools for the Project Management MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def get_velocity(
        project: str | None = None,
        last_n_sprints: int = 5,
    ) -> dict[str, Any]:
        """Get velocity data for the last N sprints.

        Args:
            project: Filter by project key (e.g., "PAYMENTS").
            last_n_sprints: Number of recent sprints to include (default 5).

        Returns:
            Velocity data with committed vs completed story points per sprint.
        """
        error_sim.maybe_error("get_velocity")
        velocity = server.load_data("velocity.json")

        results = velocity
        if project:
            results = [v for v in results if v.get("project") == project]

        # Take the last N entries
        results = results[-last_n_sprints:]

        # Calculate averages
        if results:
            avg_committed = sum(v["committed_points"] for v in results) / len(results)
            avg_completed = sum(v["completed_points"] for v in results) / len(results)
            avg_carry_over = sum(v.get("carry_over_points", 0) for v in results) / len(results)
            completion_rate = (avg_completed / avg_committed * 100) if avg_committed > 0 else 0
        else:
            avg_committed = avg_completed = avg_carry_over = completion_rate = 0

        return {
            "sprint_count": len(results),
            "velocity_data": results,
            "averages": {
                "committed_points": round(avg_committed, 1),
                "completed_points": round(avg_completed, 1),
                "carry_over_points": round(avg_carry_over, 1),
                "completion_rate_pct": round(completion_rate, 1),
            },
        }
