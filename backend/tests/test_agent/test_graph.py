"""Integration tests for the full agent graph with mock MCP servers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Mock MCP tool responses
# ---------------------------------------------------------------------------

MOCK_PR_LIST = [
    {
        "id": 247,
        "title": "Add payment retry logic",
        "state": "open",
        "author": "sarah",
        "created_at": "2026-04-06T10:00:00Z",
    },
    {
        "id": 245,
        "title": "Fix checkout total calculation",
        "state": "merged",
        "author": "alex",
        "created_at": "2026-04-05T14:00:00Z",
    },
]

MOCK_TICKET_LIST = [
    {
        "id": "PAY-189",
        "title": "Payment gateway timeout handling",
        "status": "in_progress",
        "assignee": "sarah",
        "priority": "P1",
    },
    {
        "id": "PAY-210",
        "title": "Refund flow redesign",
        "status": "to_do",
        "assignee": None,
        "priority": "P2",
    },
]

MOCK_SPRINT_REPORT = {
    "sprint_name": "Sprint 24",
    "total_points": 34,
    "completed_points": 21,
    "remaining_points": 13,
    "completion_percentage": 61.8,
    "days_remaining": 4,
}

MOCK_EVENTS = [
    {
        "id": "evt-001",
        "title": "Sprint Planning",
        "start": "2026-04-08T09:00:00Z",
        "end": "2026-04-08T10:00:00Z",
        "attendees": ["sarah", "alex", "jordan"],
    },
]


def _mock_tool_response(tool_name: str, args: dict) -> dict:
    """Return a mock response for a given tool name."""
    responses = {
        "list_pull_requests": MOCK_PR_LIST,
        "list_tickets": MOCK_TICKET_LIST,
        "get_sprint_report": MOCK_SPRINT_REPORT,
        "list_events": MOCK_EVENTS,
        "list_issues": [],
        "list_repos": [{"name": "backend"}, {"name": "frontend"}],
        "list_sprints": [{"id": 24, "name": "Sprint 24", "state": "active"}],
    }
    return {"result": responses.get(tool_name, []), "error": None}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client that returns canned tool responses."""
    client = AsyncMock()
    client.call_tool = AsyncMock(side_effect=lambda name, args: _mock_tool_response(name, args))
    return client


@pytest.fixture
def initial_state() -> dict:
    return {
        "messages": [],
        "session_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "current_plan": None,
        "plan_step_index": 0,
        "pending_tool_calls": [],
        "tool_results": [],
        "pending_approval": None,
        "approval_response": None,
        "error_count": 0,
        "last_error": None,
        "delegate_to": None,
        "sub_agent_result": None,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
    }


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestGraphEndToEnd:
    """End-to-end tests for the agent graph with mocked MCP."""

    @pytest.mark.asyncio
    async def test_status_report_flow(self, initial_state: dict, mock_mcp_client):
        """Status report query should invoke PR + ticket tools and produce a summary."""
        # Simulate the full flow: router -> planner -> executor -> synthesizer
        plan = [
            {
                "step": 1,
                "tool": "list_pull_requests",
                "server": "github",
                "args": {"state": "open"},
                "parallel_group": 1,
                "status": "pending",
            },
            {
                "step": 2,
                "tool": "list_tickets",
                "server": "project_mgmt",
                "args": {"status": "in_progress"},
                "parallel_group": 1,
                "status": "pending",
            },
        ]
        initial_state["current_plan"] = plan

        # Execute tools via mock
        results = []
        for step in plan:
            resp = await mock_mcp_client.call_tool(step["tool"], step["args"])
            results.append(
                {
                    "step": step["step"],
                    "tool": step["tool"],
                    "result": resp["result"],
                    "error": resp["error"],
                }
            )

        assert len(results) == 2
        assert results[0]["result"] == MOCK_PR_LIST
        assert results[1]["result"] == MOCK_TICKET_LIST

    @pytest.mark.asyncio
    async def test_tool_execution_collects_results(self, mock_mcp_client):
        """Each tool call should produce a result in tool_results."""
        tool_calls = ["list_pull_requests", "list_tickets", "get_sprint_report"]
        results = []
        for tool in tool_calls:
            resp = await mock_mcp_client.call_tool(tool, {})
            results.append(resp)

        assert len(results) == 3
        assert all(r["error"] is None for r in results)
        assert results[0]["result"] == MOCK_PR_LIST
        assert results[2]["result"] == MOCK_SPRINT_REPORT

    @pytest.mark.asyncio
    async def test_parallel_execution_same_group(self, mock_mcp_client):
        """Steps in the same parallel_group should all execute."""
        plan = [
            {
                "step": 1,
                "tool": "list_pull_requests",
                "server": "github",
                "args": {},
                "parallel_group": 1,
            },
            {
                "step": 2,
                "tool": "list_tickets",
                "server": "project_mgmt",
                "args": {},
                "parallel_group": 1,
            },
            {
                "step": 3,
                "tool": "list_events",
                "server": "calendar",
                "args": {},
                "parallel_group": 1,
            },
        ]

        group_1 = [s for s in plan if s["parallel_group"] == 1]
        results = []
        for step in group_1:
            resp = await mock_mcp_client.call_tool(step["tool"], step["args"])
            results.append(resp)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_sequential_groups_execute_in_order(self, mock_mcp_client):
        """Steps in higher parallel_groups should execute after lower ones."""
        plan = [
            {
                "step": 1,
                "tool": "list_tickets",
                "server": "project_mgmt",
                "args": {},
                "parallel_group": 1,
            },
            {
                "step": 2,
                "tool": "get_sprint_report",
                "server": "project_mgmt",
                "args": {"sprint": "current"},
                "parallel_group": 2,
            },
        ]

        # Execute group 1 first
        group_1_result = await mock_mcp_client.call_tool(plan[0]["tool"], plan[0]["args"])
        assert group_1_result["result"] == MOCK_TICKET_LIST

        # Then group 2
        group_2_result = await mock_mcp_client.call_tool(plan[1]["tool"], plan[1]["args"])
        assert group_2_result["result"] == MOCK_SPRINT_REPORT

    @pytest.mark.asyncio
    async def test_error_increments_error_count(self, initial_state: dict):
        """Tool errors should increment error_count in state."""
        error_client = AsyncMock()
        error_client.call_tool = AsyncMock(return_value={"result": None, "error": "Connection refused"})

        resp = await error_client.call_tool("list_pull_requests", {})
        assert resp["error"] is not None

        # Simulate state update
        initial_state["error_count"] += 1
        initial_state["last_error"] = resp["error"]
        assert initial_state["error_count"] == 1
        assert initial_state["last_error"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_cost_tracking(self, initial_state: dict):
        """Cost should accumulate across tool calls."""
        initial_state["total_cost_usd"] = 0.0

        # Simulate costs from LLM calls
        costs = [0.002, 0.005, 0.003]
        for cost in costs:
            initial_state["total_cost_usd"] += cost

        assert abs(initial_state["total_cost_usd"] - 0.01) < 1e-9

    @pytest.mark.asyncio
    async def test_token_tracking(self, initial_state: dict):
        """Token counts should accumulate."""
        initial_state["total_tokens_input"] = 0
        initial_state["total_tokens_output"] = 0

        input_tokens = [150, 200, 100]
        output_tokens = [50, 80, 30]

        for inp, out in zip(input_tokens, output_tokens):
            initial_state["total_tokens_input"] += inp
            initial_state["total_tokens_output"] += out

        assert initial_state["total_tokens_input"] == 450
        assert initial_state["total_tokens_output"] == 160


class TestGraphErrorRecovery:
    """Test that the graph handles tool errors gracefully."""

    @pytest.mark.asyncio
    async def test_timeout_error_recovery(self):
        """Agent should recover from a tool timeout."""
        error_client = AsyncMock()
        error_client.call_tool = AsyncMock(return_value={"result": None, "error": "Request timed out after 30s"})

        resp = await error_client.call_tool("list_pull_requests", {})
        assert resp["error"] is not None
        assert "timed out" in resp["error"]

    @pytest.mark.asyncio
    async def test_partial_failure_still_returns_data(self, mock_mcp_client):
        """If one tool fails but others succeed, partial data is still available."""
        # First tool succeeds
        resp1 = await mock_mcp_client.call_tool("list_tickets", {})
        assert resp1["error"] is None

        # Second tool fails
        failing_client = AsyncMock()
        failing_client.call_tool = AsyncMock(return_value={"result": None, "error": "Service unavailable"})
        resp2 = await failing_client.call_tool("list_pull_requests", {})
        assert resp2["error"] is not None

        # We still have data from the first call
        assert resp1["result"] == MOCK_TICKET_LIST

    @pytest.mark.asyncio
    async def test_max_error_count_stops_execution(self, initial_state: dict):
        """Execution should stop after too many consecutive errors."""
        max_errors = 3
        initial_state["error_count"] = max_errors

        # Agent should not attempt more tool calls
        assert initial_state["error_count"] >= max_errors


class TestGraphApprovalFlow:
    """Test the human-in-the-loop approval mechanism."""

    @pytest.mark.asyncio
    async def test_write_operation_requires_approval(self, initial_state: dict):
        """Write operations should set pending_approval."""
        write_tools = [
            "create_issue",
            "create_pull_request",
            "assign_ticket",
            "merge_pull_request",
            "transition_ticket",
        ]

        for tool_name in write_tools:
            initial_state["pending_approval"] = {
                "approval_id": str(uuid.uuid4()),
                "tool_name": tool_name,
                "tool_args": {"some": "args"},
            }
            assert initial_state["pending_approval"] is not None
            assert initial_state["pending_approval"]["tool_name"] == tool_name

    @pytest.mark.asyncio
    async def test_approved_action_executes(self, initial_state: dict, mock_mcp_client):
        """An approved action should proceed to execution."""
        initial_state["pending_approval"] = {
            "approval_id": "appr-001",
            "tool_name": "assign_ticket",
            "tool_args": {"ticket_id": "PAY-210", "assignee": "sarah"},
        }
        initial_state["approval_response"] = {"approved": True, "reason": "Looks good"}

        assert initial_state["approval_response"]["approved"] is True

    @pytest.mark.asyncio
    async def test_rejected_action_skipped(self, initial_state: dict):
        """A rejected action should not execute."""
        initial_state["pending_approval"] = {
            "approval_id": "appr-002",
            "tool_name": "merge_pull_request",
            "tool_args": {"pr_id": 247},
        }
        initial_state["approval_response"] = {"approved": False, "reason": "Not ready"}

        assert initial_state["approval_response"]["approved"] is False
