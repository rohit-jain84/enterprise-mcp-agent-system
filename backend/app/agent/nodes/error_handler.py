"""Error handler node -- retry logic and fallback behaviour."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def error_handler_node(state: AgentState) -> dict[str, Any]:
    """Handle errors from tool execution with retry or fallback.

    Strategy:
    1. For each failed step, check its per-step error count against MAX_RETRIES.
    2. Steps that still have retries left are re-queued for retry.
    3. Steps that have exceeded MAX_RETRIES are marked as exhausted and their
       failed results are dropped (the synthesizer works with partial results).
    """
    last_error = state.get("last_error", "Unknown error")
    plan = state.get("current_plan") or []
    tool_results = state.get("tool_results") or []
    step_error_counts: dict[str, int] = dict(state.get("step_error_counts") or {})

    logger.warning(
        "Error handler invoked -- step_error_counts=%s last_error=%s",
        step_error_counts,
        last_error,
    )

    # Separate failed results into retryable vs exhausted based on per-step counts
    failed_results = [r for r in tool_results if not r.get("success")]
    retry_calls: list[dict] = []
    exhausted_steps: list[int] = []

    for failed in failed_results:
        step_num = failed.get("step", 0)
        step_key = str(step_num)
        step_errors = step_error_counts.get(step_key, 0)

        if step_errors <= MAX_RETRIES:
            # This step still has retries left -- re-queue it
            for plan_step in plan:
                if plan_step["step"] == step_num:
                    plan_step["status"] = "pending"  # reset for retry
                    retry_calls.append(plan_step)
                    break
        else:
            # This step has exhausted its retries
            exhausted_steps.append(step_num)

    # Remove failed results for steps that will be retried;
    # also remove results for exhausted steps (they permanently failed)
    retrying_steps = {call["step"] for call in retry_calls}
    exhausted_step_set = set(exhausted_steps)
    cleaned_results = [
        r
        for r in tool_results
        if r.get("success") or (r.get("step") not in retrying_steps and r.get("step") not in exhausted_step_set)
    ]

    if retry_calls:
        msg = AIMessage(
            content=(
                f"[ErrorHandler] Retrying {len(retry_calls)} failed tool call(s). "
                f"Per-step counts: {step_error_counts}. "
                f"Error: {last_error}"
            ),
            name="error_handler",
        )
        if exhausted_steps:
            msg = AIMessage(
                content=(
                    f"[ErrorHandler] Retrying {len(retry_calls)} call(s); "
                    f"{len(exhausted_steps)} step(s) exhausted retries "
                    f"(steps {exhausted_steps}). Error: {last_error}"
                ),
                name="error_handler",
            )

        logger.info(
            "Retrying %d calls; %d steps exhausted retries",
            len(retry_calls),
            len(exhausted_steps),
        )

        return {
            "messages": [msg],
            "pending_tool_calls": retry_calls,
            "tool_results": cleaned_results,
            "current_plan": plan,
            "last_error": None,
        }
    else:
        # All failed steps have exhausted their retries -- fall back to synthesizer
        successful_results = [r for r in tool_results if r.get("success")]
        if successful_results:
            msg = AIMessage(
                content=(
                    f"[ErrorHandler] Max retries ({MAX_RETRIES}) exceeded for all "
                    f"failed steps. Proceeding with {len(successful_results)} "
                    f"successful result(s). Last error: {last_error}"
                ),
                name="error_handler",
            )
        else:
            msg = AIMessage(
                content=(
                    f"[ErrorHandler] All tool calls failed after {MAX_RETRIES} retries "
                    f"per step. Last error: {last_error}. Generating error response."
                ),
                name="error_handler",
            )

        logger.error(
            "All failed steps exhausted retries -- falling back with %d/%d results",
            len(successful_results),
            len(tool_results),
        )

        return {
            "messages": [msg],
            "pending_tool_calls": [],
            "tool_results": successful_results,
            "last_error": last_error,
        }
