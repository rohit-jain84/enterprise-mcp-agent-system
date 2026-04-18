"""Conditional edge functions for the LangGraph agent."""

from __future__ import annotations

import logging
from typing import Literal

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def route_after_router(
    state: AgentState,
) -> Literal["planner", "delegate", "synthesizer"]:
    """Decide where to go after the router node.

    Reads the last router message to extract the intent.
    """
    # The router stores the intent in an internal key; fall back to parsing
    # the message content if the key isn't present.
    intent = state.get("_router_intent")  # type: ignore[typeddict-item]

    if intent is None:
        # Parse from the last router message
        for msg in reversed(state.get("messages", [])):
            if getattr(msg, "name", None) == "router":
                content = msg.content
                if "needs_tools" in content:
                    intent = "needs_tools"
                elif "needs_delegation" in content:
                    intent = "needs_delegation"
                else:
                    intent = "direct_answer"
                break

    if intent == "needs_tools":
        logger.info("Routing to planner")
        return "planner"
    elif intent == "needs_delegation":
        logger.info("Routing to delegate")
        return "delegate"
    else:
        logger.info("Routing to synthesizer (direct answer)")
        return "synthesizer"


def route_after_tool_executor(
    state: AgentState,
) -> Literal["approval_gate", "tool_executor", "error_handler", "synthesizer"]:
    """Decide where to go after tool execution.

    Checks for:
    1. Errors that need handling.
    2. Write operations that need approval.
    3. More pending tool calls to execute.
    4. All done -- go to synthesizer.
    """
    last_error = state.get("last_error")
    error_count = state.get("error_count", 0)

    # If there were errors, route to error handler
    if last_error and error_count > 0:
        logger.info("Routing to error_handler (error_count=%d)", error_count)
        return "error_handler"

    # If there's a pending approval, route to approval gate
    pending_approval = state.get("pending_approval")
    if pending_approval is not None:
        logger.info("Routing to approval_gate")
        return "approval_gate"

    # If there are more pending calls, continue executing
    pending = state.get("pending_tool_calls") or []
    if pending:
        logger.info("Routing back to tool_executor (%d calls pending)", len(pending))
        return "tool_executor"

    # All done
    logger.info("Routing to synthesizer (all tools complete)")
    return "synthesizer"


def route_after_approval(
    state: AgentState,
) -> Literal["tool_executor", "synthesizer"]:
    """Route based on approval decision.

    If approved, continue with tool execution. If denied, skip to synthesizer.
    """
    approval = state.get("approval_response")
    if approval and approval.get("approved"):
        logger.info("Approval granted -- continuing to tool_executor")
        return "tool_executor"
    else:
        logger.info("Approval denied -- routing to synthesizer")
        return "synthesizer"


def route_after_error_handler(
    state: AgentState,
) -> Literal["tool_executor", "synthesizer"]:
    """Route after error handling.

    If there are retry calls queued, go back to tool_executor.
    Otherwise fall back to synthesizer.
    """
    pending = state.get("pending_tool_calls") or []
    if pending:
        logger.info("Error handler queued %d retries -- routing to tool_executor", len(pending))
        return "tool_executor"
    else:
        logger.info("Error handler exhausted retries -- routing to synthesizer")
        return "synthesizer"
