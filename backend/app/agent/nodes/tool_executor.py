"""Tool executor node -- runs pending MCP tool calls, optionally in parallel."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import AIMessage

from app.agent.state import AgentState
from app.mcp.client import get_mcp_client
from app.mcp.registry import is_write_tool

logger = logging.getLogger(__name__)


async def _execute_single_call(
    call: dict[str, Any],
) -> dict[str, Any]:
    """Execute one tool call and return the result dict."""
    tool_name = call["tool"]
    server = call.get("server", "")
    args = call.get("args", {})
    step = call.get("step", 0)

    mcp = await get_mcp_client()
    start = time.monotonic()

    try:
        if server:
            result = await mcp.call_tool(server, tool_name, args)
        else:
            result = await mcp.call_tool_by_name(tool_name, args)
        elapsed = time.monotonic() - start
        logger.info("Tool %s completed in %.2fs", tool_name, elapsed)
        return {
            "step": step,
            "tool": tool_name,
            "server": server,
            "args": args,
            "result": result,
            "success": True,
            "duration_ms": round(elapsed * 1000),
        }
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.exception("Tool %s failed after %.2fs", tool_name, elapsed)
        return {
            "step": step,
            "tool": tool_name,
            "server": server,
            "args": args,
            "result": None,
            "error": str(exc),
            "success": False,
            "duration_ms": round(elapsed * 1000),
        }


async def tool_executor_node(state: AgentState) -> dict[str, Any]:
    """Execute all pending tool calls, running independent ones in parallel.

    After execution, determines whether more steps remain in the plan and
    queues them, or signals completion.
    """
    pending = state.get("pending_tool_calls") or []
    if not pending:
        logger.warning("Tool executor called with no pending tool calls")
        return {
            "messages": [AIMessage(content="[ToolExecutor] No pending tool calls.", name="tool_executor")],
        }

    # Execute all calls in the current batch concurrently
    tasks = [_execute_single_call(call) for call in pending]
    results = await asyncio.gather(*tasks)
    results_list: list[dict] = list(results)

    # Accumulate results
    existing_results = list(state.get("tool_results") or [])
    existing_results.extend(results_list)

    # Check for errors and track per-step error counts
    errors = [r for r in results_list if not r["success"]]
    last_error = errors[-1]["error"] if errors else None
    error_count = state.get("error_count", 0) + len(errors)
    step_error_counts = dict(state.get("step_error_counts") or {})
    for err in errors:
        step_key = str(err.get("step", 0))
        step_error_counts[step_key] = step_error_counts.get(step_key, 0) + 1

    # Update plan step statuses
    plan = state.get("current_plan") or []
    for result in results_list:
        for step in plan:
            if step["step"] == result["step"]:
                step["status"] = "done" if result["success"] else "error"

    # Determine next batch from plan
    completed_steps = {r["step"] for r in existing_results}
    next_pending: list[dict] = []

    if plan:
        remaining = [s for s in plan if s["step"] not in completed_steps and s["status"] == "pending"]
        if remaining:
            next_group = min(s["parallel_group"] for s in remaining)
            next_pending = [s for s in remaining if s["parallel_group"] == next_group]

    # Check if any pending calls are write operations (for approval gate)
    has_writes = any(is_write_tool(call["tool"]) for call in pending)
    pending_approval = None
    if has_writes:
        # Find the first write tool that was in this batch
        for call in pending:
            if is_write_tool(call["tool"]):
                import uuid

                pending_approval = {
                    "approval_id": str(uuid.uuid4()),
                    "tool_name": call["tool"],
                    "tool_args": call.get("args", {}),
                }
                break

    # Build summary message
    success_count = sum(1 for r in results_list if r["success"])
    fail_count = len(results_list) - success_count
    summary = f"[ToolExecutor] Executed {len(results_list)} tools: {success_count} succeeded, {fail_count} failed."
    if next_pending:
        summary += f" {len(next_pending)} more calls queued."

    return {
        "messages": [AIMessage(content=summary, name="tool_executor")],
        "tool_results": existing_results,
        "pending_tool_calls": next_pending,
        "current_plan": plan,
        "pending_approval": pending_approval,
        "error_count": error_count,
        "step_error_counts": step_error_counts,
        "last_error": last_error,
    }
