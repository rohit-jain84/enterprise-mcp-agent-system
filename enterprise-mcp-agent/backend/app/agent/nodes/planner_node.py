"""Planner node -- decomposes a request into ordered tool calls via Claude Sonnet."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, SystemMessage

from app.agent.prompts import PLANNER_FEW_SHOT, PLANNER_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

_SONNET_INPUT_COST = 3.0 / 1_000_000
_SONNET_OUTPUT_COST = 15.0 / 1_000_000


async def planner_node(state: AgentState) -> dict[str, Any]:
    """Produce an execution plan -- a list of tool call steps.

    The plan is stored in ``current_plan`` and the first batch of calls is
    placed into ``pending_tool_calls``.
    """
    settings = get_settings()
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=2048,
        temperature=0.0,
    )

    # Build few-shot messages
    few_shot_msgs: list = []
    for entry in PLANNER_FEW_SHOT:
        from langchain_core.messages import HumanMessage as HM, AIMessage as AM
        if entry["role"] == "user":
            few_shot_msgs.append(HM(content=entry["content"]))
        else:
            few_shot_msgs.append(AM(content=entry["content"]))

    prompt_messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        *few_shot_msgs,
        *state["messages"],
    ]

    response = await llm.ainvoke(prompt_messages)

    usage = response.usage_metadata or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    # Parse the plan JSON
    raw = response.content.strip()
    # Strip markdown fences if the model wrapped them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        plan: list[dict] = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Planner returned invalid JSON: %s", raw)
        return {
            "messages": [AIMessage(content="[Planner] Failed to create a valid plan.", name="planner")],
            "current_plan": None,
            "last_error": "Planner produced invalid JSON",
            "error_count": state.get("error_count", 0) + 1,
            "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
            "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
            "total_cost_usd": state.get("total_cost_usd", 0.0)
            + input_tokens * _SONNET_INPUT_COST
            + output_tokens * _SONNET_OUTPUT_COST,
        }

    # Normalise each step
    for step in plan:
        step.setdefault("status", "pending")
        step.setdefault("parallel_group", step.get("step", 1))

    # Identify the first parallel group to execute
    if plan:
        first_group = min(s["parallel_group"] for s in plan)
        pending = [s for s in plan if s["parallel_group"] == first_group]
    else:
        pending = []

    logger.info("Planner created %d-step plan, first batch=%d calls", len(plan), len(pending))

    plan_msg = AIMessage(
        content=f"[Planner] Created {len(plan)}-step plan with {len(set(s['parallel_group'] for s in plan))} parallel groups.",
        name="planner",
    )

    return {
        "messages": [plan_msg],
        "current_plan": plan,
        "plan_step_index": 0,
        "pending_tool_calls": pending,
        "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
        "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0)
        + input_tokens * _SONNET_INPUT_COST
        + output_tokens * _SONNET_OUTPUT_COST,
    }
