"""Availability tools for the Calendar MCP server."""

from typing import Any

from fastmcp import FastMCP
from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator


def register_tools(mcp: FastMCP, server: BaseMCPServer, error_sim: ErrorSimulator) -> None:
    @mcp.tool()
    def check_availability(
        username: str,
        date: str,
    ) -> dict[str, Any]:
        """Check free/busy availability for a person on a specific date.

        Args:
            username: The person's username (e.g., "sarah.chen").
            date: The date to check (ISO format, e.g., "2026-04-08").

        Returns:
            Free/busy time slots for the person on that date.
        """
        error_sim.maybe_error("check_availability")
        availability = server.load_data("availability.json")

        for entry in availability:
            if entry["username"] == username:
                for day in entry.get("days", []):
                    if day["date"] == date:
                        busy_slots = [s for s in day["slots"] if s["status"] == "busy"]
                        free_slots = [s for s in day["slots"] if s["status"] == "free"]
                        return {
                            "username": username,
                            "date": date,
                            "busy_slots": busy_slots,
                            "free_slots": free_slots,
                            "total_busy_hours": len(busy_slots) * 0.5,
                            "total_free_hours": len(free_slots) * 0.5,
                        }
                return {
                    "username": username,
                    "date": date,
                    "busy_slots": [],
                    "free_slots": [],
                    "message": f"No availability data for {username} on {date}",
                }

        return {"error": f"User {username} not found in availability data"}
