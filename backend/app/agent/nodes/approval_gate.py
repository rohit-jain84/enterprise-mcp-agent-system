"""Approval gate node -- pauses execution for human-in-the-loop approval."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT_SECONDS = 15 * 60  # 15 minutes


async def approval_gate_node(state: AgentState) -> dict[str, Any]:
    """Check if the current execution requires human approval.

    If ``pending_approval`` is set, this node uses LangGraph's ``interrupt()``
    to pause graph execution.  The graph will resume when the human responds
    via the approval endpoint, and the response will be in
    ``approval_response``.

    A timeout check ensures stale approvals (>15 min) are auto-denied.
    """
    pending = state.get("pending_approval")
    if pending is None:
        # No approval needed -- pass through
        logger.debug("No pending approval -- passing through")
        return {}

    tool_name = pending.get("tool_name", "unknown")
    tool_args = pending.get("tool_args", {})
    approval_id = pending.get("approval_id", "")
    requested_at = pending.get("requested_at")

    logger.info(
        "Approval required for tool=%s approval_id=%s",
        tool_name,
        approval_id,
    )

    # Check if the approval has already expired before interrupting
    if requested_at:
        try:
            req_time = datetime.fromisoformat(requested_at)
            elapsed = (datetime.now(UTC) - req_time).total_seconds()
            if elapsed > APPROVAL_TIMEOUT_SECONDS:
                logger.warning(
                    "Approval timed out for tool=%s approval_id=%s elapsed=%.0fs",
                    tool_name,
                    approval_id,
                    elapsed,
                )
                msg = AIMessage(
                    content=(
                        f"[ApprovalGate] Action **{tool_name}** timed out after "
                        f"{int(elapsed // 60)} minutes without a response. "
                        f"The action was not executed."
                    ),
                    name="approval_gate",
                )
                return {
                    "messages": [msg],
                    "approval_response": {"approved": False, "reason": "timeout"},
                    "pending_approval": None,
                }
        except (ValueError, TypeError):
            pass  # If timestamp is malformed, proceed normally

    # Pause the graph and wait for human input.
    # The interrupt value is sent to the client so they know what to approve.
    approval_response = interrupt(
        {
            "type": "approval_request",
            "approval_id": approval_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "message": (
                f"The agent wants to execute **{tool_name}** with the following "
                f"arguments. Please approve or deny this action."
            ),
        }
    )

    # Check for timeout again when the graph resumes (human may have responded late)
    if requested_at:
        try:
            req_time = datetime.fromisoformat(requested_at)
            elapsed = (datetime.now(UTC) - req_time).total_seconds()
            if elapsed > APPROVAL_TIMEOUT_SECONDS:
                logger.warning("Approval response arrived after timeout for %s", approval_id)
                msg = AIMessage(
                    content=f"[ApprovalGate] Action **{tool_name}** expired — response arrived too late.",
                    name="approval_gate",
                )
                return {
                    "messages": [msg],
                    "approval_response": {"approved": False, "reason": "timeout"},
                    "pending_approval": None,
                }
        except (ValueError, TypeError):
            pass

    # When the graph resumes, `approval_response` contains the human's decision.
    approved = approval_response.get("approved", False)
    reason = approval_response.get("reason", "")

    logger.info(
        "Approval response for %s: approved=%s reason=%s",
        approval_id,
        approved,
        reason,
    )

    if approved:
        msg = AIMessage(
            content=f"[ApprovalGate] Action **{tool_name}** approved by user.",
            name="approval_gate",
        )
    else:
        msg = AIMessage(
            content=f"[ApprovalGate] Action **{tool_name}** denied by user. Reason: {reason or 'none given'}",
            name="approval_gate",
        )

    return {
        "messages": [msg],
        "approval_response": {
            "approved": approved,
            "reason": reason,
        },
        "pending_approval": None,
    }
