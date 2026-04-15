"""Triage sub-agent -- batch ticket analysis and prioritisation."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.prompts import TRIAGE_AGENT_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.config import get_settings
from app.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

_GPT4O_INPUT_COST = 2.50 / 1_000_000
_GPT4O_OUTPUT_COST = 10.0 / 1_000_000

_FILTER_EXTRACTION_PROMPT = """\
You are a filter extraction assistant. Given a user's triage request, determine \
the appropriate filters for fetching tickets from a project management system.

Available filter fields:
- "status": ticket status (e.g. "open", "closed", "in_progress")
- "assignee": who the ticket is assigned to (e.g. "unassigned", or a person's name)
- "priority": ticket priority (e.g. "high", "critical", "low", "medium")
- "label" or "tag": ticket labels/tags
- "type": ticket type (e.g. "bug", "feature", "task")

Respond with ONLY a JSON object of filter key-value pairs. Examples:
- User says "triage all open tickets" -> {"status": "open"}
- User says "triage high priority tickets" -> {"priority": "high"}
- User says "triage unassigned tickets" -> {"status": "open", "assignee": "unassigned"}
- User says "triage critical bugs" -> {"priority": "critical", "type": "bug"}
- User says "triage open high priority bugs" -> {"status": "open", "priority": "high", "type": "bug"}
- User says "triage tickets" (no specific filter) -> {"status": "open"}

If the user's intent is unclear or very general, default to {"status": "open"}.
Respond with ONLY the JSON object, no explanation."""


async def _extract_ticket_filters(
    llm: ChatOpenAI, query: str,
) -> dict[str, str]:
    """Use the LLM to parse the user's query into ticket filters."""
    if not query.strip():
        return {"status": "open"}

    try:
        response = await llm.ainvoke([
            SystemMessage(content=_FILTER_EXTRACTION_PROMPT),
            HumanMessage(content=query),
        ])
        filters = json.loads(response.content.strip())
        if isinstance(filters, dict) and filters:
            logger.info("Extracted ticket filters from query: %s", filters)
            return filters
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Failed to extract filters from query, using defaults: %s", exc)

    return {"status": "open"}


async def triage_agent_node(state: AgentState) -> dict[str, Any]:
    """Run the triage sub-agent.

    1. Parse the user's query to determine ticket filters.
    2. Fetch matching tickets from the project management MCP.
    3. Analyse each ticket with GPT-4o.
    4. Produce a triage report with priority and assignee recommendations.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        max_tokens=4096,
        temperature=0.1,
    )

    # Extract context from the user's message
    query = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break

    mcp = await get_mcp_client()

    # Step 1: Parse user query to determine appropriate filters
    ticket_filters = await _extract_ticket_filters(llm, query)
    logger.info("Triage agent fetching tickets with filters: %s", ticket_filters)

    # Step 2: Fetch tickets that match the filters
    try:
        tickets_response = await mcp.call_tool(
            "project_mgmt",
            "list_tickets",
            ticket_filters,
        )
        tickets = tickets_response.get("tickets", tickets_response.get("result", []))
    except Exception as exc:
        logger.exception("Failed to fetch tickets for triage")
        return {
            "messages": [AIMessage(
                content=f"[Triage] Failed to fetch tickets: {exc}",
                name="triage_agent",
            )],
            "sub_agent_result": f"Error fetching tickets: {exc}",
            "delegate_to": None,
        }

    filter_desc = ", ".join(f"{k}={v}" for k, v in ticket_filters.items())
    if not tickets:
        return {
            "messages": [AIMessage(
                content=f"[Triage] No tickets found matching filters: {filter_desc}.",
                name="triage_agent",
            )],
            "sub_agent_result": f"No tickets found matching filters: {filter_desc}.",
            "delegate_to": None,
        }

    logger.info("Triage agent analysing %d tickets", len(tickets))

    # Step 2: Ask the LLM to triage
    tickets_block = json.dumps(tickets, indent=2, default=str)
    triage_prompt = [
        SystemMessage(content=TRIAGE_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User request: {query}\n\n"
            f"Tickets to triage ({len(tickets)} total):\n"
            f"```json\n{tickets_block}\n```\n\n"
            f"Please analyse and produce a triage report."
        )),
    ]

    response = await llm.ainvoke(triage_prompt)

    usage = response.usage_metadata or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    report = response.content
    logger.info("Triage agent produced %d-char report for %d tickets", len(report), len(tickets))

    return {
        "messages": [AIMessage(
            content=f"[Triage] Analysed {len(tickets)} tickets.",
            name="triage_agent",
        )],
        "sub_agent_result": report,
        "delegate_to": None,
        "total_tokens_input": state.get("total_tokens_input", 0) + input_tokens,
        "total_tokens_output": state.get("total_tokens_output", 0) + output_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0)
        + input_tokens * _GPT4O_INPUT_COST
        + output_tokens * _GPT4O_OUTPUT_COST,
    }
