"""Router node -- classifies user intent via Claude Haiku."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.prompts import ROUTER_FEW_SHOT, ROUTER_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

# Cost per token for Haiku (rough estimates for tracking).
_HAIKU_INPUT_COST = 0.25 / 1_000_000   # $0.25 per 1M input tokens
_HAIKU_OUTPUT_COST = 1.25 / 1_000_000   # $1.25 per 1M output tokens


def _build_few_shot_messages() -> list[HumanMessage | AIMessage]:
    """Convert the few-shot list into LangChain message objects."""
    msgs: list[HumanMessage | AIMessage] = []
    for entry in ROUTER_FEW_SHOT:
        if entry["role"] == "user":
            msgs.append(HumanMessage(content=entry["content"]))
        else:
            msgs.append(AIMessage(content=entry["content"]))
    return msgs


async def router_node(state: AgentState) -> dict[str, Any]:
    """Classify the user's intent and set routing metadata in state.

    Returns partial state update with ``delegate_to`` and an AI message
    containing the raw classification JSON.
    """
    settings = get_settings()
    llm = ChatAnthropic(
        model="claude-haiku-4-20250414",
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=256,
        temperature=0.0,
    )

    # Build the prompt: system + few-shot + conversation history
    prompt_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        *_build_few_shot_messages(),
        *state["messages"],
    ]

    response = await llm.ainvoke(prompt_messages)

    # Track token usage
    usage = response.usage_metadata or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    # Parse the classification JSON
    raw = response.content.strip()
    try:
        classification = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Router returned non-JSON: %s -- defaulting to direct_answer", raw)
        classification = {
            "intent": "direct_answer",
            "delegate_to": None,
            "reasoning": "Failed to parse router output",
        }

    intent = classification.get("intent", "direct_answer")
    delegate_to = classification.get("delegate_to")
    reasoning = classification.get("reasoning", "")

    logger.info("Router classified intent=%s delegate_to=%s reason=%s", intent, delegate_to, reasoning)

    # Store the routing decision in the messages for downstream nodes
    router_msg = AIMessage(
        content=f"[Router] Intent: {intent} | Delegate: {delegate_to} | {reasoning}",
        name="router",
    )

    return {
        "messages": [router_msg],
        "delegate_to": delegate_to if intent == "needs_delegation" else None,
        "pending_tool_calls": [],
        "current_plan": None,
        "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
        "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0)
        + input_tokens * _HAIKU_INPUT_COST
        + output_tokens * _HAIKU_OUTPUT_COST,
        # Stash the intent for the conditional edge function
        "_router_intent": intent,
    }
