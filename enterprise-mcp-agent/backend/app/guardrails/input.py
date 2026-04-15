"""Input guardrails -- validates and sanitises the incoming user message.

Called by the ``guardrails_input`` node in the LangGraph agent graph.
Combines NeMo Guardrails policy checks with Presidio PII redaction.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.config import get_settings
from app.guardrails.pii_detector import PIIDetector
from app.guardrails.rails import GuardrailsWrapper

logger = logging.getLogger(__name__)

# Module-level singletons (initialised lazily).
_guardrails: GuardrailsWrapper | None = None
_pii_detector: PIIDetector | None = None


async def _get_guardrails() -> GuardrailsWrapper:
    global _guardrails
    if _guardrails is None:
        _guardrails = GuardrailsWrapper()
        await _guardrails.initialize()
    return _guardrails


def _get_pii_detector() -> PIIDetector:
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = PIIDetector()
    return _pii_detector


async def run_input_guardrails(state: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the latest user message through guardrails and PII detection.

    Returns
    -------
    dict | None
        A state patch to merge into the graph state, or ``None`` if the
        message passes all checks unchanged.  When the message is blocked,
        an ``AIMessage`` refusal is appended to ``messages`` so the graph
        can short-circuit to the output node.
    """
    settings = get_settings()
    if not settings.GUARDRAILS_ENABLED:
        return None

    # Extract the latest user message from the conversation.
    messages = state.get("messages", [])
    if not messages:
        return None

    last_msg = messages[-1]
    user_text: str = getattr(last_msg, "content", "")
    if not user_text:
        return None

    # --- Step 1: NeMo Guardrails policy check ---
    try:
        guardrails = await _get_guardrails()
        allowed, rejection = await guardrails.check_input(user_text)
        if not allowed:
            logger.info("Input blocked by NeMo Guardrails: %s", rejection)
            return {
                "messages": [AIMessage(content=rejection or "I'm unable to process that request.")],
            }
    except Exception:
        logger.exception("NeMo Guardrails check failed; continuing without policy check")

    # --- Step 2: PII redaction ---
    try:
        pii = _get_pii_detector()
        if pii.available:
            detections = pii.scan(user_text)
            if detections:
                redacted = pii.redact(user_text)
                logger.info(
                    "PII redacted from input: %d entities",
                    len(detections),
                )
                # Replace the user message content with the redacted version.
                # We rebuild the message to preserve metadata.
                from langchain_core.messages import HumanMessage

                patched_msg = HumanMessage(content=redacted)
                return {"messages": [patched_msg]}
    except Exception:
        logger.exception("PII detection failed; continuing with original message")

    return None
