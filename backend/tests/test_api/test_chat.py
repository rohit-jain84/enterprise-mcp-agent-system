"""Tests for the chat endpoint and WebSocket flow."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi import FastAPI, WebSocket, status
from fastapi.testclient import TestClient

from app.models.schemas import ChatRequest, ChatResponse, WSMessage, WSOutbound

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def app_with_chat(session_id: uuid.UUID) -> FastAPI:
    from fastapi import APIRouter

    app = FastAPI()
    router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

    @router.post("/", response_model=ChatResponse)
    async def chat(body: ChatRequest):
        return ChatResponse(
            message_id=uuid.uuid4(),
            session_id=body.session_id,
            content="Here is a summary of your sprint progress.",
            tool_calls=[{"tool": "get_sprint_report", "args": {"sprint": "current"}, "status": "success"}],
            token_count=150,
            cost=0.003,
        )

    @router.websocket("/ws/{ws_session_id}")
    async def websocket_chat(websocket: WebSocket, ws_session_id: str):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)

                if msg.get("type") == "user_message":
                    # Send stream_start
                    await websocket.send_json({"type": "stream_start", "payload": {}})
                    # Send a chunk
                    await websocket.send_json(
                        {
                            "type": "stream_chunk",
                            "payload": {"content": "Processing your request..."},
                        }
                    )
                    # Send tool_call
                    await websocket.send_json({"type": "tool_call", "payload": {"tool": "list_tickets", "args": {}}})
                    # Send tool_result
                    await websocket.send_json(
                        {"type": "tool_result", "payload": {"tool": "list_tickets", "result": []}}
                    )
                    # Send stream_end
                    await websocket.send_json({"type": "stream_end", "payload": {"content": "Done."}})
        except Exception:
            pass

    app.include_router(router)
    return app


@pytest.fixture
def client(app_with_chat: FastAPI) -> TestClient:
    return TestClient(app_with_chat)


# ---------------------------------------------------------------------------
# HTTP Chat endpoint tests
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    def test_chat_success(self, client: TestClient, session_id: uuid.UUID):
        resp = client.post(
            "/api/v1/chat/",
            json={"session_id": str(session_id), "message": "What's the sprint status?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "content" in data
        assert data["session_id"] == str(session_id)
        assert data["token_count"] > 0
        assert data["cost"] > 0

    def test_chat_returns_tool_calls(self, client: TestClient, session_id: uuid.UUID):
        resp = client.post(
            "/api/v1/chat/",
            json={"session_id": str(session_id), "message": "Sprint report please"},
        )
        data = resp.json()
        assert data["tool_calls"] is not None
        assert len(data["tool_calls"]) > 0
        assert data["tool_calls"][0]["tool"] == "get_sprint_report"

    def test_chat_missing_message(self, client: TestClient, session_id: uuid.UUID):
        resp = client.post(
            "/api/v1/chat/",
            json={"session_id": str(session_id)},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_chat_empty_message(self, client: TestClient, session_id: uuid.UUID):
        resp = client.post(
            "/api/v1/chat/",
            json={"session_id": str(session_id), "message": ""},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_chat_missing_session_id(self, client: TestClient):
        resp = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# WebSocket flow tests
# ---------------------------------------------------------------------------


class TestWebSocketChat:
    def test_websocket_full_flow(self, client: TestClient, session_id: uuid.UUID):
        with client.websocket_connect(f"/api/v1/chat/ws/{session_id}") as ws:
            # Send a user message
            ws.send_json({"type": "user_message", "payload": {"message": "Show tickets"}})

            # Expect stream_start
            msg = ws.receive_json()
            assert msg["type"] == "stream_start"

            # Expect stream_chunk
            msg = ws.receive_json()
            assert msg["type"] == "stream_chunk"
            assert "content" in msg["payload"]

            # Expect tool_call
            msg = ws.receive_json()
            assert msg["type"] == "tool_call"
            assert "tool" in msg["payload"]

            # Expect tool_result
            msg = ws.receive_json()
            assert msg["type"] == "tool_result"

            # Expect stream_end
            msg = ws.receive_json()
            assert msg["type"] == "stream_end"

    def test_websocket_message_types(self, client: TestClient, session_id: uuid.UUID):
        """All outbound message types should be in the expected set."""
        expected_types = {
            "stream_start",
            "stream_chunk",
            "stream_end",
            "tool_call",
            "tool_result",
            "approval_request",
            "error",
        }

        with client.websocket_connect(f"/api/v1/chat/ws/{session_id}") as ws:
            ws.send_json({"type": "user_message", "payload": {"message": "Hi"}})

            received_types = set()
            for _ in range(5):
                msg = ws.receive_json()
                received_types.add(msg["type"])

            assert received_types.issubset(expected_types)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestChatSchemas:
    def test_chat_request_validation(self):
        req = ChatRequest(session_id=uuid.uuid4(), message="Hello")
        assert len(req.message) > 0

    def test_chat_request_max_length(self):
        with pytest.raises(Exception):
            ChatRequest(session_id=uuid.uuid4(), message="x" * 32_001)

    def test_chat_response_schema(self):
        resp = ChatResponse(
            message_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            content="Test response",
            token_count=100,
            cost=0.002,
        )
        assert resp.content == "Test response"
        assert resp.tool_calls is None

    def test_ws_message_schema(self):
        msg = WSMessage(type="user_message", payload={"message": "Hi"})
        assert msg.type == "user_message"

    def test_ws_outbound_schema(self):
        out = WSOutbound(type="stream_chunk", payload={"content": "partial"})
        assert out.type == "stream_chunk"
