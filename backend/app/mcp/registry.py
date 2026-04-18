"""Tool discovery and registration -- maps tool names to servers and categories."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.mcp.client import MCPClientManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Write-operation detection
# ---------------------------------------------------------------------------

# Tools whose names start with any of these prefixes are considered *write*
# operations and require human approval before execution.
_WRITE_PREFIXES: tuple[str, ...] = (
    "create_",
    "update_",
    "delete_",
    "merge_",
    "assign_",
    "transition_",
    "add_",
)

# Explicit overrides (tool name -> is_write).
_WRITE_OVERRIDES: dict[str, bool] = {
    "get_diff": False,
    "list_repos": False,
    "list_pull_requests": False,
    "list_issues": False,
    "list_commits": False,
    "list_projects": False,
    "list_tickets": False,
    "list_sprints": False,
    "list_events": False,
    "list_attendees": False,
    "get_pull_request": False,
    "get_ticket": False,
    "get_event": False,
    "get_sprint_report": False,
    "find_free_slots": False,
}


def is_write_tool(tool_name: str) -> bool:
    """Return True if the tool is classified as a write (mutating) operation."""
    if tool_name in _WRITE_OVERRIDES:
        return _WRITE_OVERRIDES[tool_name]
    return any(tool_name.startswith(prefix) for prefix in _WRITE_PREFIXES)


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


@dataclass
class RegisteredTool:
    """Metadata for a single registered tool."""

    name: str
    server: str
    description: str
    input_schema: dict[str, Any]
    is_write: bool


class ToolRegistry:
    """Discovers tools from MCPClientManager and indexes them for fast lookup."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    async def refresh(self, mcp: MCPClientManager) -> None:
        """Re-discover tools from the MCP client manager and rebuild the index."""
        self._tools.clear()
        for raw_tool in mcp.list_tools():
            name = raw_tool["name"]
            self._tools[name] = RegisteredTool(
                name=name,
                server=raw_tool.get("server", "unknown"),
                description=raw_tool.get("description", ""),
                input_schema=raw_tool.get("inputSchema", {}),
                is_write=is_write_tool(name),
            )
        logger.info(
            "ToolRegistry refreshed -- %d tools (%d write)",
            len(self._tools),
            sum(1 for t in self._tools.values() if t.is_write),
        )

    def get(self, tool_name: str) -> RegisteredTool | None:
        return self._tools.get(tool_name)

    def all_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def read_tools(self) -> list[RegisteredTool]:
        return [t for t in self._tools.values() if not t.is_write]

    def write_tools(self) -> list[RegisteredTool]:
        return [t for t in self._tools.values() if t.is_write]

    def tools_for_server(self, server: str) -> list[RegisteredTool]:
        return [t for t in self._tools.values() if t.server == server]

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# Module-level singleton
_registry: ToolRegistry | None = None


async def get_tool_registry(mcp: MCPClientManager) -> ToolRegistry:
    """Return the singleton ToolRegistry, refreshing on first call."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        await _registry.refresh(mcp)
    return _registry
