"""MCP Client Manager -- connects to all MCP servers and invokes tools."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    base_url: str
    healthy: bool = False
    tools: list[dict] = field(default_factory=list)


class MCPClientManager:
    """Manages connections to all MCP servers and exposes a unified tool API.

    Each MCP server exposes an HTTP+SSE transport.  This manager discovers
    available tools on startup and routes ``call_tool`` requests to the
    correct server.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._servers: dict[str, MCPServerConfig] = {
            "github": MCPServerConfig(
                name="github",
                base_url=settings.GITHUB_MCP_URL,
            ),
            "project_mgmt": MCPServerConfig(
                name="project_mgmt",
                base_url=settings.PROJECT_MGMT_MCP_URL,
            ),
            "calendar": MCPServerConfig(
                name="calendar",
                base_url=settings.CALENDAR_MCP_URL,
            ),
        }
        self._http: httpx.AsyncClient | None = None
        self._tool_to_server: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Open the shared HTTP client and discover tools from each server."""
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        await self._discover_all()

    async def close(self) -> None:
        """Shut down the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def _discover_all(self) -> None:
        """Discover tools from every configured server concurrently."""
        tasks = [self._discover_server(srv) for srv in self._servers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(
            "Tool discovery complete -- %d tools across %d servers",
            len(self._tool_to_server),
            sum(1 for s in self._servers.values() if s.healthy),
        )

    # Static tool manifest for each MCP server. The servers expose FastMCP's
    # SSE transport which does not publish a REST ``/tools/list`` endpoint, so
    # we advertise the tool names here and consider a server healthy as long
    # as the SSE endpoint responds.
    _TOOL_MANIFEST: dict[str, list[str]] = {
        "github": [
            "get_ci_status", "list_commits", "list_issues", "get_issue_details",
            "list_pull_requests", "get_pr_details", "get_pr_diff",
            "create_issue", "add_comment", "add_labels",
        ],
        "project_mgmt": [
            "get_backlog", "get_assignments", "list_sprints", "get_sprint_details",
            "list_tickets", "get_ticket_details", "get_velocity",
            "update_ticket_priority", "update_ticket_assignee",
            "update_ticket_labels", "move_ticket",
        ],
        "calendar": [
            "check_availability", "list_meetings", "get_meeting_details",
            "get_attendees", "get_meeting_notes",
        ],
    }

    async def _discover_server(self, server: MCPServerConfig) -> None:
        """Probe the MCP server's SSE endpoint and load its tool manifest."""
        assert self._http is not None
        try:
            async with self._http.stream(
                "GET", f"{server.base_url}/sse", timeout=5.0,
            ) as resp:
                healthy = resp.status_code == 200
        except Exception:
            healthy = False
            logger.exception("Failed to reach %s SSE endpoint", server.name)

        server.healthy = healthy
        if healthy:
            tool_names = self._TOOL_MANIFEST.get(server.name, [])
            server.tools = [{"name": n, "description": ""} for n in tool_names]
            for n in tool_names:
                self._tool_to_server[n] = server.name
            logger.info(
                "MCP server %s reachable; %d tools registered",
                server.name, len(tool_names),
            )

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a tool on the specified MCP server.

        Args:
            server_name: Logical name of the server (github, project_mgmt, calendar).
            tool_name: Name of the tool to call.
            args: Arguments to pass to the tool.

        Returns:
            The tool result payload as a dict.

        Raises:
            ValueError: If the server is unknown or unhealthy.
            httpx.HTTPStatusError: On non-2xx responses.
        """
        assert self._http is not None
        server = self._servers.get(server_name)
        if server is None:
            raise ValueError(f"Unknown MCP server: {server_name}")
        if not server.healthy:
            raise ValueError(f"MCP server '{server_name}' is not healthy")

        logger.info("Calling tool %s on %s with args %s", tool_name, server_name, args)

        resp = await self._http.post(
            f"{server.base_url}/tools/call",
            json={
                "name": tool_name,
                "arguments": args,
            },
        )
        resp.raise_for_status()
        result = resp.json()
        logger.debug("Tool %s returned: %s", tool_name, result)
        return result

    async def call_tool_by_name(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a tool by name -- the server is resolved automatically."""
        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            raise ValueError(
                f"Tool '{tool_name}' not found on any server. "
                f"Available tools: {list(self._tool_to_server.keys())}"
            )
        return await self.call_tool(server_name, tool_name, args)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all available tools across every healthy server."""
        all_tools: list[dict[str, Any]] = []
        for server in self._servers.values():
            if not server.healthy:
                continue
            for tool in server.tools:
                all_tools.append(
                    {
                        **tool,
                        "server": server.name,
                    }
                )
        return all_tools

    def get_server_for_tool(self, tool_name: str) -> str | None:
        """Return the server name that provides the given tool, or None."""
        return self._tool_to_server.get(tool_name)

    async def health_check(self) -> dict[str, bool]:
        """Probe each server's SSE endpoint and return a name -> healthy mapping."""
        results: dict[str, bool] = {}
        for server in self._servers.values():
            try:
                assert self._http is not None
                async with self._http.stream(
                    "GET", f"{server.base_url}/sse", timeout=5.0,
                ) as resp:
                    healthy = resp.status_code == 200
            except Exception:
                healthy = False
            server.healthy = healthy
            results[server.name] = healthy
        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: MCPClientManager | None = None


async def get_mcp_client() -> MCPClientManager:
    """Return the singleton MCPClientManager, starting it if needed."""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
        await _manager.start()
    return _manager


async def close_mcp_client() -> None:
    """Shut down the singleton client on app shutdown."""
    global _manager
    if _manager is not None:
        await _manager.close()
        _manager = None
