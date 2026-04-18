"""Chat service -- orchestrates LangGraph agent invocation."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.database import User
from app.models.enums import MessageRole
from app.models.schemas import ChatResponse
from app.services.cost_tracker import CostTracker, calculate_cost
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an enterprise AI assistant with access to MCP (Model Context Protocol) \
tools for GitHub, project management, and calendar operations. You help users manage their \
development workflow efficiently.

When using tools:
- Always explain what you are about to do before calling a tool.
- If a tool requires approval, wait for user confirmation.
- Summarize tool results clearly.
- Track and report any errors.

Be concise, professional, and proactive in suggesting follow-up actions."""


AsyncCallback = Callable[..., Coroutine[Any, Any, None]]


class ChatService:
    """Direct LLM invocation service used by the REST/WebSocket chat endpoints.

    NOTE: This service provides a simple, non-agentic chat path — it calls the
    LLM directly without MCP tools, planning, or approval workflows.  The full
    agentic flow (tool execution, approval gate, sub-agents) is handled by the
    LangGraph agent graph in ``app.agent.graph``.  Both paths share the same
    session/message persistence and cost tracking.
    """

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        user: User | None = None,
    ) -> None:
        self._db = db
        self._settings = settings
        self._user = user
        self._session_svc = SessionService(db)
        self._cost_tracker = CostTracker()

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model="gpt-4o",
            api_key=self._settings.OPENAI_API_KEY,
            max_tokens=4096,
            streaming=True,
        )

    async def _load_history(self, session_id: uuid.UUID) -> list:
        """Load previous messages for context."""
        session = await self._db.get(
            __import__("app.models.database", fromlist=["Session"]).Session,
            session_id,
        )
        if session is None:
            return []

        from sqlalchemy import select

        from app.models.database import Message

        result = await self._db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(50)  # Keep context window manageable
        )
        messages = result.scalars().all()

        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                history.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                history.append(SystemMessage(content=msg.content))
        return history

    async def invoke(self, session_id: uuid.UUID, user_message: str) -> ChatResponse:
        """Synchronous (non-streaming) invocation -- send message, return full response."""
        # Persist user message
        user_msg = await self._session_svc.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message,
        )

        # Build message list
        history = await self._load_history(session_id)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=user_message)]

        # Invoke LLM
        llm = self._build_llm()
        response = await llm.ainvoke(messages)

        # Extract usage
        input_tokens = (
            getattr(response, "usage_metadata", {}).get("input_tokens", 0)
            if hasattr(response, "usage_metadata") and response.usage_metadata
            else 0
        )
        output_tokens = (
            getattr(response, "usage_metadata", {}).get("output_tokens", 0)
            if hasattr(response, "usage_metadata") and response.usage_metadata
            else 0
        )
        cost = calculate_cost(input_tokens, output_tokens)

        # Persist assistant message
        assistant_msg = await self._session_svc.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            token_count=input_tokens + output_tokens,
            cost=cost,
        )

        # Update session totals
        await self._session_svc.update_session_costs(session_id, input_tokens + output_tokens, cost)

        # Track cost in Redis
        if self._user:
            try:
                await self._cost_tracker.record_usage(
                    session_id=session_id,
                    user_id=self._user.id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception:
                logger.warning("Failed to record usage in Redis", exc_info=True)

        return ChatResponse(
            message_id=assistant_msg.id,
            session_id=session_id,
            content=response.content,
            token_count=input_tokens + output_tokens,
            cost=cost,
        )

    async def invoke_streaming(
        self,
        session_id: uuid.UUID,
        user_message: str,
        on_chunk: AsyncCallback | None = None,
        on_tool_call: AsyncCallback | None = None,
        on_tool_result: AsyncCallback | None = None,
        on_approval_request: AsyncCallback | None = None,
    ) -> dict:
        """Streaming invocation -- calls callbacks as tokens arrive."""
        # Persist user message
        await self._session_svc.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message,
        )

        # Build message list
        history = await self._load_history(session_id)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=user_message)]

        llm = self._build_llm()

        full_content = ""
        input_tokens = 0
        output_tokens = 0

        async for event in llm.astream(messages):
            if hasattr(event, "content") and event.content:
                chunk_text = event.content
                full_content += chunk_text
                if on_chunk:
                    await on_chunk(chunk_text)

            # Capture tool calls if present
            if hasattr(event, "tool_calls") and event.tool_calls:
                for tc in event.tool_calls:
                    if on_tool_call:
                        await on_tool_call(tc.get("name", ""), tc.get("args", {}))

            # Capture usage from final event
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                input_tokens = event.usage_metadata.get("input_tokens", input_tokens)
                output_tokens = event.usage_metadata.get("output_tokens", output_tokens)

        cost = calculate_cost(input_tokens, output_tokens)

        # Persist assistant message
        assistant_msg = await self._session_svc.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=full_content,
            token_count=input_tokens + output_tokens,
            cost=cost,
        )

        await self._session_svc.update_session_costs(session_id, input_tokens + output_tokens, cost)

        return {
            "message_id": str(assistant_msg.id),
            "token_count": input_tokens + output_tokens,
            "cost": cost,
        }
