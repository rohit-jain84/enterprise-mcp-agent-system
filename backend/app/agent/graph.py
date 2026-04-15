"""LangGraph StateGraph definition for the enterprise MCP agent."""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.checkpointer import get_checkpointer
from app.agent.edges import (
    route_after_approval,
    route_after_error_handler,
    route_after_router,
    route_after_tool_executor,
)
from app.agent.nodes.approval_gate import approval_gate_node
from app.agent.nodes.error_handler import error_handler_node
from app.agent.nodes.planner_node import planner_node
from app.agent.nodes.router_node import router_node
from app.agent.nodes.synthesizer_node import synthesizer_node
from app.agent.nodes.tool_executor import tool_executor_node
from app.agent.state import AgentState
from app.agent.subagents.research_agent import research_agent_node
from app.agent.subagents.triage_agent import triage_agent_node

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guardrail stubs (thin wrappers -- real logic lives in app.guardrails)
# ---------------------------------------------------------------------------

async def guardrails_input_node(state: AgentState) -> dict:
    """Input guardrails -- validates / sanitises the incoming user message."""
    try:
        from app.guardrails.input import run_input_guardrails

        result = await run_input_guardrails(state)
        if result:
            return result
    except Exception:
        logger.exception("Input guardrails failed -- skipping")
    return {}


async def guardrails_output_node(state: AgentState) -> dict:
    """Output guardrails -- validates / sanitises the outgoing response."""
    try:
        from app.guardrails.output import run_output_guardrails

        result = await run_output_guardrails(state)
        if result:
            return result
    except Exception:
        logger.exception("Output guardrails failed -- skipping")
    return {}


# ---------------------------------------------------------------------------
# Delegate dispatcher
# ---------------------------------------------------------------------------

async def delegate_node(state: AgentState) -> dict:
    """Dispatch to the appropriate sub-agent based on ``delegate_to``."""
    target = state.get("delegate_to")
    if target == "research":
        return await research_agent_node(state)
    elif target == "triage":
        return await triage_agent_node(state)
    else:
        logger.warning("Unknown delegation target: %s -- falling through", target)
        return {"sub_agent_result": f"Unknown delegation target: {target}"}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct the full LangGraph StateGraph (uncompiled).

    Call ``compile()`` on the returned graph with a checkpointer to get a
    runnable.
    """
    graph = StateGraph(AgentState)

    # ---- Add nodes ----
    graph.add_node("guardrails_input", guardrails_input_node)
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("delegate", delegate_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("guardrails_output", guardrails_output_node)

    # ---- Edges ----

    # START -> guardrails_input -> router
    graph.add_edge(START, "guardrails_input")
    graph.add_edge("guardrails_input", "router")

    # Router conditional: needs_tools -> planner | needs_delegation -> delegate | direct_answer -> synthesizer
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "planner": "planner",
            "delegate": "delegate",
            "synthesizer": "synthesizer",
        },
    )

    # Planner always goes to tool_executor
    graph.add_edge("planner", "tool_executor")

    # Tool executor conditional: approval_gate | more tools | error_handler | synthesizer
    graph.add_conditional_edges(
        "tool_executor",
        route_after_tool_executor,
        {
            "approval_gate": "approval_gate",
            "tool_executor": "tool_executor",
            "error_handler": "error_handler",
            "synthesizer": "synthesizer",
        },
    )

    # Approval gate conditional: approved -> tool_executor | denied -> synthesizer
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "tool_executor": "tool_executor",
            "synthesizer": "synthesizer",
        },
    )

    # Error handler conditional: retry -> tool_executor | fallback -> synthesizer
    graph.add_conditional_edges(
        "error_handler",
        route_after_error_handler,
        {
            "tool_executor": "tool_executor",
            "synthesizer": "synthesizer",
        },
    )

    # Delegate goes to synthesizer
    graph.add_edge("delegate", "synthesizer")

    # Synthesizer -> output guardrails -> END
    graph.add_edge("synthesizer", "guardrails_output")
    graph.add_edge("guardrails_output", END)

    return graph


# ---------------------------------------------------------------------------
# Compiled graph factory
# ---------------------------------------------------------------------------

_compiled_graph = None


async def get_compiled_graph():
    """Return a compiled graph with PostgreSQL checkpointing.

    The graph is compiled once and cached for the lifetime of the process.
    Thread-safety is provided by LangGraph's internal machinery; the
    ``thread_id`` config (set to ``session_id``) isolates state per session.
    """
    global _compiled_graph

    if _compiled_graph is not None:
        return _compiled_graph

    checkpointer = await get_checkpointer()
    graph = build_graph()
    _compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],  # HITL: pause before approval
    )

    logger.info("LangGraph agent compiled with AsyncPostgresSaver checkpointer")
    return _compiled_graph


async def run_agent(
    session_id: str,
    user_id: str,
    user_message: str,
) -> dict:
    """Convenience function to invoke the agent graph for a single user turn.

    Args:
        session_id: Unique conversation session (used as LangGraph thread_id).
        user_id: Authenticated user identifier.
        user_message: The new user message.

    Returns:
        The final agent state after the graph completes (or interrupts).
    """
    from langchain_core.messages import HumanMessage

    compiled = await get_compiled_graph()

    input_state: dict = {
        "messages": [HumanMessage(content=user_message)],
        "session_id": session_id,
        "user_id": user_id,
        "current_plan": None,
        "plan_step_index": 0,
        "pending_tool_calls": [],
        "tool_results": [],
        "pending_approval": None,
        "approval_response": None,
        "error_count": 0,
        "step_error_counts": {},
        "last_error": None,
        "delegate_to": None,
        "sub_agent_result": None,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
    }

    config = {"configurable": {"thread_id": session_id}}

    result = await compiled.ainvoke(input_state, config=config)
    return result


async def resume_after_approval(
    session_id: str,
    approval_response: dict,
) -> dict:
    """Resume a graph that was interrupted at the approval gate.

    Args:
        session_id: The session whose graph is paused.
        approval_response: {"approved": bool, "reason": str | None}.

    Returns:
        The final agent state after the graph completes.
    """
    compiled = await get_compiled_graph()
    config = {"configurable": {"thread_id": session_id}}

    # LangGraph resumes from the interrupt point with the provided value.
    result = await compiled.ainvoke(
        {"approval_response": approval_response},
        config=config,
    )
    return result
