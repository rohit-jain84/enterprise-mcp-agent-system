"""Synthesizer node -- generates the final markdown response via GPT-4o."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import SYNTHESIZER_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings

logger = logging.getLogger(__name__)

_GPT4O_INPUT_COST = 2.50 / 1_000_000
_GPT4O_OUTPUT_COST = 10.0 / 1_000_000


async def synthesizer_node(state: AgentState) -> dict[str, Any]:
    """Generate the user-facing response from tool results / sub-agent output.

    Builds a context block from all collected data and asks GPT-4o to produce
    a polished Markdown answer.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        max_tokens=4096,
        temperature=0.2,
    )

    # Gather context for the synthesizer
    context_parts: list[str] = []

    # Tool results
    tool_results = state.get("tool_results") or []
    if tool_results:
        context_parts.append("## Tool Results\n")
        for idx, tr in enumerate(tool_results, 1):
            status = "OK" if tr.get("success") else "ERROR"
            context_parts.append(
                f"### Tool Call {idx}: {tr.get('tool', 'unknown')} [{status}]\n"
                f"**Args:** {json.dumps(tr.get('args', {}), indent=2)}\n"
                f"**Result:** {json.dumps(tr.get('result'), indent=2, default=str)}\n"
            )
            if not tr.get("success"):
                context_parts.append(f"**Error:** {tr.get('error', 'Unknown error')}\n")

    # Sub-agent result
    sub_result = state.get("sub_agent_result")
    if sub_result:
        context_parts.append(f"## Sub-Agent Report\n\n{sub_result}\n")

    # If there's nothing to synthesize (direct answer), just pass conversation through
    if not context_parts:
        prompt_messages = [
            SystemMessage(
                content=(
                    "You are a helpful enterprise assistant. Answer the user's "
                    "question directly and concisely in Markdown."
                )
            ),
            *state["messages"],
        ]
    else:
        context_block = "\n".join(context_parts)
        prompt_messages = [
            SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
            *state["messages"],
            HumanMessage(
                content=(
                    f"Here is the data collected from enterprise systems:\n\n"
                    f"{context_block}\n\n"
                    f"Please synthesize a complete response for the user."
                )
            ),
        ]

    response = await llm.ainvoke(prompt_messages)

    usage = response.usage_metadata or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    logger.info("Synthesizer produced %d chars", len(response.content))

    return {
        "messages": [AIMessage(content=response.content, name="synthesizer")],
        "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
        "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0)
        + input_tokens * _GPT4O_INPUT_COST
        + output_tokens * _GPT4O_OUTPUT_COST,
    }
