"""MCP tool wrappers exposed as LangChain-compatible tools."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool

from app.mcp.client import MCPClientManager
from app.mcp.registry import ToolRegistry

logger = logging.getLogger(__name__)


def _make_tool(
    tool_name: str,
    description: str,
    server: str,
    input_schema: dict[str, Any],
    mcp: MCPClientManager,
) -> StructuredTool:
    """Create a LangChain StructuredTool that delegates to the MCP client."""

    async def _invoke(**kwargs: Any) -> dict[str, Any]:
        logger.info("LangChain tool '%s' invoked with %s", tool_name, kwargs)
        return await mcp.call_tool(server, tool_name, kwargs)

    # Build a minimal JSON schema for the tool args.
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    return StructuredTool.from_function(
        coroutine=_invoke,
        name=tool_name,
        description=description or f"Call the {tool_name} tool on {server}",
        args_schema=None,  # We pass raw kwargs through
    )


async def build_langchain_tools(
    mcp: MCPClientManager,
    registry: ToolRegistry,
) -> list[StructuredTool]:
    """Build LangChain StructuredTool instances for every discovered MCP tool.

    These tools can be bound to a ChatAnthropic model or passed directly to
    LangGraph tool nodes.
    """
    tools: list[StructuredTool] = []
    for reg_tool in registry.all_tools():
        lc_tool = _make_tool(
            tool_name=reg_tool.name,
            description=reg_tool.description,
            server=reg_tool.server,
            input_schema=reg_tool.input_schema,
            mcp=mcp,
        )
        tools.append(lc_tool)
    logger.info("Built %d LangChain tools from MCP registry", len(tools))
    return tools
