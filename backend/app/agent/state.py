"""LangGraph agent state definition."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state flowing through every node in the agent graph.

    Attributes:
        messages: Conversation history managed via LangGraph's add_messages reducer.
        session_id: Unique identifier for this conversation session.
        user_id: Authenticated user making the request.
        current_plan: Ordered list of planned steps produced by the planner node.
            Each entry: {"step": int, "tool": str, "args": dict, "status": str,
                         "parallel_group": int | None}.
        plan_step_index: Index into current_plan for the next step to execute.
        pending_tool_calls: Tool calls queued for execution.
        tool_results: Accumulated results from executed tool calls.
        pending_approval: Set when a write operation needs human approval.
            Format: {"approval_id": str, "tool_name": str, "tool_args": dict}.
        approval_response: Human response to a pending approval request.
            Format: {"approved": bool, "reason": str | None}.
        error_count: Total number of errors encountered (kept for backwards compat).
        step_error_counts: Per-step error counts keyed by step number (str).
            Used by the error handler to enforce per-step retry limits.
        last_error: Description of the most recent error.
        delegate_to: Sub-agent to delegate to ('research' | 'triage').
        sub_agent_result: Result string returned by a sub-agent.
        total_tokens_input: Cumulative input tokens used across all LLM calls.
        total_tokens_output: Cumulative output tokens used across all LLM calls.
        total_cost_usd: Cumulative estimated cost in USD.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    user_id: str
    current_plan: list[dict] | None
    plan_step_index: int
    pending_tool_calls: list[dict]
    tool_results: list[dict]
    pending_approval: dict | None
    approval_response: dict | None
    error_count: int
    step_error_counts: dict[str, int]
    last_error: str | None
    delegate_to: str | None
    sub_agent_result: str | None
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
