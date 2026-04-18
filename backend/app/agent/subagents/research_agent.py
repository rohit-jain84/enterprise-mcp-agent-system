"""Research sub-agent -- multi-step information gathering and cross-referencing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings
from app.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

_GPT4O_INPUT_COST = 2.50 / 1_000_000
_GPT4O_OUTPUT_COST = 10.0 / 1_000_000


async def _research_plan(llm: ChatOpenAI, query: str, available_tools: list[dict]) -> list[dict]:
    """Ask the LLM to produce a research plan given available tools."""
    tool_summary = "\n".join(
        f"- **{t['name']}** ({t.get('server', '?')}): {t.get('description', 'No description')}" for t in available_tools
    )
    planning_prompt = [
        SystemMessage(
            content=(
                "You are a research planner. Given a research question and available tools, "
                "produce a JSON array of data-gathering steps. Each step: "
                '{"step": N, "tool": "tool_name", "server": "server_name", "args": {...}, "purpose": "why"}.\n\n'
                f"Available tools:\n{tool_summary}"
            )
        ),
        HumanMessage(content=query),
    ]
    resp = await llm.ainvoke(planning_prompt)
    raw = resp.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Research planner produced invalid JSON: %s", raw)
        return []


async def _execute_research_step(step: dict) -> dict:
    """Execute a single research data-gathering step."""
    mcp = await get_mcp_client()
    tool_name = step["tool"]
    server = step.get("server", "")
    args = step.get("args", {})

    try:
        if server:
            result = await mcp.call_tool(server, tool_name, args)
        else:
            result = await mcp.call_tool_by_name(tool_name, args)
        return {"step": step.get("step", 0), "tool": tool_name, "result": result, "success": True}
    except Exception as exc:
        logger.exception("Research step %s failed", tool_name)
        return {"step": step.get("step", 0), "tool": tool_name, "error": str(exc), "success": False}


async def research_agent_node(state: AgentState) -> dict[str, Any]:
    """Run the research sub-agent.

    1. Plan data-gathering steps.
    2. Execute them (parallelising where possible).
    3. Synthesise a research report.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        max_tokens=4096,
        temperature=0.1,
    )

    # Extract the user's research query from the last human message
    query = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break

    if not query:
        return {
            "messages": [AIMessage(content="[Research] No research query found.", name="research_agent")],
            "sub_agent_result": "No research query provided.",
        }

    # Discover available tools
    mcp = await get_mcp_client()
    available_tools = mcp.list_tools()

    # Phase 1: Plan
    plan = await _research_plan(llm, query, available_tools)
    if not plan:
        return {
            "messages": [AIMessage(content="[Research] Could not create research plan.", name="research_agent")],
            "sub_agent_result": "Failed to plan research steps.",
        }

    logger.info("Research agent planned %d data-gathering steps", len(plan))

    # Phase 2: Execute (all steps in parallel for simplicity)
    tasks = [_execute_research_step(step) for step in plan]
    results = await asyncio.gather(*tasks)
    results_list = list(results)

    # Phase 3: Synthesise
    results_block = json.dumps(results_list, indent=2, default=str)
    synthesis_prompt = [
        SystemMessage(content=RESEARCH_AGENT_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Research question: {query}\n\n"
                f"Data gathered:\n```json\n{results_block}\n```\n\n"
                f"Please synthesise a research report."
            )
        ),
    ]
    synthesis_resp = await llm.ainvoke(synthesis_prompt)

    usage = synthesis_resp.usage_metadata or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    report = synthesis_resp.content

    logger.info("Research agent produced %d-char report", len(report))

    return {
        "messages": [AIMessage(content=f"[Research] Report generated ({len(report)} chars).", name="research_agent")],
        "sub_agent_result": report,
        "delegate_to": None,
        "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
        "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0)
        + input_tokens * _GPT4O_INPUT_COST
        + output_tokens * _GPT4O_OUTPUT_COST,
    }
