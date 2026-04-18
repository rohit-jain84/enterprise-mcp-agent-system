"""MCP server status endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPServerResponse(BaseModel):
    id: str
    name: str
    url: str
    status: str
    toolCount: int
    lastHealthCheck: str | None = None
    version: str | None = None
    error: str | None = None


@router.get("/servers", response_model=list[MCPServerResponse])
async def list_mcp_servers():
    """Return the status of all configured MCP servers."""
    try:
        client = await get_mcp_client()
    except Exception as exc:
        logger.warning("Failed to get MCP client: %s", exc)
        return []

    health = await client.health_check()
    now = datetime.now(UTC).isoformat()

    servers: list[MCPServerResponse] = []
    for name, server in client._servers.items():
        is_healthy = health.get(name, False)
        servers.append(
            MCPServerResponse(
                id=name,
                name=name.replace("_", " ").title(),
                url=server.base_url,
                status="connected" if is_healthy else "disconnected",
                toolCount=len(server.tools),
                lastHealthCheck=now,
                error=None if is_healthy else f"Server at {server.base_url} is unreachable",
            )
        )

    return servers
