"""Output guardrails -- validates and sanitises the outgoing agent response.

Called by the ``guardrails_output`` node in the LangGraph agent graph.
Combines NeMo Guardrails output filtering with Presidio PII redaction.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.config import get_settings
from app.guardrails.pii_detector import PIIDetector
from app.guardrails.rails import GuardrailsWrapper

logger = logging.getLogger(__name__)

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


async def run_output_guardrails(state: dict[str, Any]) -> dict[str, Any] | None:
    """Filter the latest assistant message through output guardrails and PII redaction.

    Returns
    -------
    dict | None
        A state patch with a replacement ``AIMessage`` if the response was
        modified, or ``None`` if no changes were needed.
    """
    settings = get_settings()
    if not settings.GUARDRAILS_ENABLED:
        return None

    # Find the latest assistant message.
    messages = state.get("messages", [])
    if not messages:
        return None

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return None

    response_text: str = last_msg.content or ""
    if not response_text:
        return None

    modified = False
    filtered_text = response_text

    # --- Step 1: NeMo Guardrails output filtering ---
    try:
        guardrails = await _get_guardrails()
        if guardrails.enabled:
            filtered_text = await guardrails.check_output(filtered_text)
            if filtered_text != response_text:
                modified = True
                logger.info("Output modified by NeMo Guardrails")
    except Exception:
        logger.exception("NeMo Guardrails output check failed; continuing with original")

    # --- Step 2: PII redaction on output ---
    try:
        pii = _get_pii_detector()
        if pii.available:
            detections = pii.scan(filtered_text)
            if detections:
                filtered_text = pii.redact(filtered_text)
                modified = True
                logger.info(
                    "PII redacted from output: %d entities",
                    len(detections),
                )
    except Exception:
        logger.exception("PII redaction on output failed; continuing with current text")

    if modified:
        return {"messages": [AIMessage(content=filtered_text)]}

    return None
