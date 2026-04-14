"""Evaluation runner for the Enterprise MCP Agent System.

Loads tasks from eval_tasks.json, runs each task through the agent pipeline,
scores results, and generates a report.

Usage::

    # Run all tasks
    python -m tests.eval.eval_runner

    # Run a single category
    python -m tests.eval.eval_runner --category STATUS_REPORT

    # Run a specific task
    python -m tests.eval.eval_runner --task-id 1

    # Dry-run (validate tasks only, no agent calls)
    python -m tests.eval.eval_runner --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.eval.eval_scorers import (
    composite_score,
    cost_score,
    exact_match_score,
    pass_fail_score,
    rubric_score,
    tool_usage_score,
)

logger = logging.getLogger(__name__)

TASKS_PATH = Path(__file__).parent / "eval_tasks.json"

# Default weights for composite scoring
DEFAULT_WEIGHTS = {
    "quality": 0.40,
    "tool_usage": 0.25,
    "cost": 0.15,
    "pass_fail": 0.20,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    task_id: int
    category: str
    input_text: str
    response: str = ""
    tool_calls: list[str] = field(default_factory=list)
    actual_cost_usd: float = 0.0
    quality_score: float = 0.0
    tool_usage_score: float = 0.0
    cost_score: float = 0.0
    composite: float = 0.0
    passed: bool = False
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class EvalReport:
    results: list[TaskResult] = field(default_factory=list)
    overall_score: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0


# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------

def load_tasks(
    path: Path = TASKS_PATH,
    category: str | None = None,
    task_id: int | None = None,
) -> list[dict[str, Any]]:
    """Load evaluation tasks from JSON, optionally filtering."""
    with open(path, "r", encoding="utf-8") as fh:
        tasks: list[dict[str, Any]] = json.load(fh)

    if task_id is not None:
        tasks = [t for t in tasks if t["id"] == task_id]
    elif category is not None:
        tasks = [t for t in tasks if t["category"] == category.upper()]

    if not tasks:
        raise ValueError(
            f"No tasks found (category={category!r}, task_id={task_id!r})"
        )

    return tasks


# ---------------------------------------------------------------------------
# Mock agent runner (used when the real agent is unavailable)
# ---------------------------------------------------------------------------

async def _run_agent_mock(task: dict[str, Any]) -> dict[str, Any]:
    """Placeholder agent runner that returns an empty response.

    Replace this with the real agent invocation once the graph is wired up.
    """
    return {
        "response": "",
        "tool_calls": [],
        "cost_usd": 0.0,
    }


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

async def run_agent(task: dict[str, Any]) -> dict[str, Any]:
    """Run a single evaluation task through the agent.

    Attempts to import and invoke the real agent graph.  Falls back to the
    mock runner if the agent is not available.

    Returns a dict with keys: response, tool_calls, cost_usd.
    """
    try:
        # Try importing the real agent graph
        from app.agent.state import AgentState
        from langgraph.graph import StateGraph

        # Placeholder -- the real invocation will be wired to the compiled
        # graph once the agent nodes are fully implemented.
        raise ImportError("Agent graph not yet wired for eval")
    except ImportError:
        return await _run_agent_mock(task)


# ---------------------------------------------------------------------------
# Scoring dispatcher
# ---------------------------------------------------------------------------

async def score_task(task: dict[str, Any], result: dict[str, Any]) -> dict[str, float]:
    """Score a single task result using the appropriate scoring method."""
    response = result["response"]
    method = task["scoring_method"]
    criteria = task.get("scoring_criteria", {})
    expected_tools = task.get("expected_tools", [])
    max_cost = task.get("max_cost_usd", 1.0)
    actual_cost = result.get("cost_usd", 0.0)
    tool_calls = result.get("tool_calls", [])

    scores: dict[str, float] = {}

    # Quality score based on method
    if method == "rubric":
        scores["quality"] = await rubric_score(response, criteria)
    elif method == "exact_match":
        scores["quality"] = exact_match_score(response, criteria)
    elif method in ("pass_fail", "factual"):
        scores["quality"] = pass_fail_score(response, criteria)
    else:
        logger.warning("Unknown scoring method %r, defaulting to pass_fail", method)
        scores["quality"] = pass_fail_score(response, criteria)

    # Tool usage
    scores["tool_usage"] = tool_usage_score(tool_calls, expected_tools)

    # Cost
    scores["cost"] = cost_score(actual_cost, max_cost)

    # Composite
    scores["composite"] = composite_score(scores, DEFAULT_WEIGHTS)

    return scores


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(report: EvalReport) -> str:
    """Generate a human-readable Markdown evaluation report."""
    lines: list[str] = []
    lines.append("# Evaluation Report")
    lines.append("")
    lines.append(f"**Overall Score:** {report.overall_score:.1%}")
    lines.append(f"**Pass / Fail / Error:** {report.pass_count} / {report.fail_count} / {report.error_count}")
    lines.append(f"**Total Cost:** ${report.total_cost_usd:.4f}")
    lines.append(f"**Total Duration:** {report.total_duration_seconds:.1f}s")
    lines.append("")
    lines.append("## Results by Task")
    lines.append("")
    lines.append("| ID | Category | Status | Quality | Tools | Cost | Composite | USD | Time |")
    lines.append("|----|----------|--------|---------|-------|------|-----------|-----|------|")

    for r in report.results:
        status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
        lines.append(
            f"| {r.task_id} | {r.category} | {status} | "
            f"{r.quality_score:.0%} | {r.tool_usage_score:.0%} | "
            f"{r.cost_score:.0%} | {r.composite:.0%} | "
            f"${r.actual_cost_usd:.4f} | {r.duration_seconds:.1f}s |"
        )

    # Per-category summary
    lines.append("")
    lines.append("## Results by Category")
    lines.append("")

    categories: dict[str, list[TaskResult]] = {}
    for r in report.results:
        categories.setdefault(r.category, []).append(r)

    for cat, results in sorted(categories.items()):
        avg = sum(r.composite for r in results) / len(results) if results else 0
        passed = sum(1 for r in results if r.passed)
        lines.append(f"- **{cat}**: {avg:.0%} avg score, {passed}/{len(results)} passed")

    # Failures detail
    failures = [r for r in report.results if not r.passed]
    if failures:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for r in failures:
            reason = r.error if r.error else f"Composite score {r.composite:.0%} < 0.7"
            lines.append(f"- **Task {r.task_id}** ({r.category}): {reason}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

PASS_THRESHOLD = 0.70


async def run_eval(
    category: str | None = None,
    task_id: int | None = None,
    dry_run: bool = False,
) -> EvalReport:
    """Run the full evaluation pipeline."""
    tasks = load_tasks(category=category, task_id=task_id)
    report = EvalReport()

    logger.info("Running %d evaluation tasks", len(tasks))

    for task in tasks:
        tr = TaskResult(
            task_id=task["id"],
            category=task["category"],
            input_text=task["input"],
        )

        if dry_run:
            tr.passed = True
            tr.composite = 1.0
            report.results.append(tr)
            report.pass_count += 1
            continue

        start = time.monotonic()
        try:
            result = await run_agent(task)
            tr.response = result["response"]
            tr.tool_calls = result.get("tool_calls", [])
            tr.actual_cost_usd = result.get("cost_usd", 0.0)

            scores = await score_task(task, result)
            tr.quality_score = scores.get("quality", 0.0)
            tr.tool_usage_score = scores.get("tool_usage", 0.0)
            tr.cost_score = scores.get("cost", 0.0)
            tr.composite = scores.get("composite", 0.0)
            tr.passed = tr.composite >= PASS_THRESHOLD

        except Exception as exc:
            tr.error = str(exc)
            tr.passed = False
            report.error_count += 1
            logger.exception("Task %d failed with error", task["id"])

        tr.duration_seconds = time.monotonic() - start
        report.results.append(tr)

        if tr.passed:
            report.pass_count += 1
        elif not tr.error:
            report.fail_count += 1

        report.total_cost_usd += tr.actual_cost_usd

    # Compute overall score
    if report.results:
        report.overall_score = (
            sum(r.composite for r in report.results) / len(report.results)
        )
    report.total_duration_seconds = sum(r.duration_seconds for r in report.results)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation suite")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Run only tasks in this category (e.g. STATUS_REPORT, TICKET_TRIAGE)",
    )
    parser.add_argument(
        "--task-id",
        type=int,
        default=None,
        help="Run a single task by ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate tasks without running the agent",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write the report to a file (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of Markdown",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    report = asyncio.run(
        run_eval(
            category=args.category,
            task_id=args.task_id,
            dry_run=args.dry_run,
        )
    )

    if args.json_output:
        output = json.dumps(
            {
                "overall_score": report.overall_score,
                "pass_count": report.pass_count,
                "fail_count": report.fail_count,
                "error_count": report.error_count,
                "total_cost_usd": report.total_cost_usd,
                "total_duration_seconds": report.total_duration_seconds,
                "results": [
                    {
                        "task_id": r.task_id,
                        "category": r.category,
                        "passed": r.passed,
                        "composite": r.composite,
                        "quality_score": r.quality_score,
                        "tool_usage_score": r.tool_usage_score,
                        "cost_score": r.cost_score,
                        "actual_cost_usd": r.actual_cost_usd,
                        "duration_seconds": r.duration_seconds,
                        "error": r.error,
                    }
                    for r in report.results
                ],
            },
            indent=2,
        )
    else:
        output = generate_report(report)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)

    # Exit with non-zero if any tasks failed
    if report.fail_count > 0 or report.error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
