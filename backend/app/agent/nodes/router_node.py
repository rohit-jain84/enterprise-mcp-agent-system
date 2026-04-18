"""Router node -- classifies user intent via GPT-4o-mini."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import ROUTER_FEW_SHOT, ROUTER_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

# Cost per token for GPT-4o-mini (rough estimates for tracking).
_GPT4O_MINI_INPUT_COST = 0.15 / 1_000_000  # $0.15 per 1M input tokens
_GPT4O_MINI_OUTPUT_COST = 0.60 / 1_000_000  # $0.60 per 1M output tokens

_last_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}


async def invoke_llm(messages: list[Any]) -> str:
    """Invoke the router LLM and return raw string content.

    Side-effect: records usage in ``_last_usage`` for the caller.
    Extracted so tests can monkeypatch without touching ChatOpenAI.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.OPENAI_API_KEY,
        max_tokens=256,
        temperature=0.0,
    )
    response = await llm.ainvoke(messages)
    usage = response.usage_metadata or {}
    _last_usage["input_tokens"] = usage.get("input_tokens", 0)
    _last_usage["output_tokens"] = usage.get("output_tokens", 0)
    return response.content


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
    # Build the prompt: system + few-shot + conversation history
    prompt_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        *_build_few_shot_messages(),
        *state["messages"],
    ]

    raw_content = await invoke_llm(prompt_messages)
    input_tokens = _last_usage["input_tokens"]
    output_tokens = _last_usage["output_tokens"]

    # Parse the classification JSON
    raw = raw_content.strip()
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
        + input_tokens * _GPT4O_MINI_INPUT_COST
        + output_tokens * _GPT4O_MINI_OUTPUT_COST,
        # Stash the intent for the conditional edge function
        "_router_intent": intent,
    }
