"""Tests for session CRUD operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.models.schemas import SessionCreate, SessionResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_session(
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    title: str = "New Chat",
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(session_id or uuid.uuid4()),
        "user_id": str(user_id or uuid.uuid4()),
        "title": title,
        "total_tokens": 0,
        "total_cost": 0.0,
        "created_at": now,
        "updated_at": now,
    }


# In-memory session store for testing
_sessions: dict[str, dict] = {}


@pytest.fixture(autouse=True)
def _clear_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def app_with_sessions(user_id: uuid.UUID) -> FastAPI:
    from fastapi import APIRouter

    app = FastAPI()
    router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

    @router.post("/", status_code=status.HTTP_201_CREATED)
    async def create_session(body: SessionCreate):
        session = _make_session(user_id=user_id, title=body.title)
        _sessions[session["id"]] = session
        return session

    @router.get("/")
    async def list_sessions():
        return list(_sessions.values())

    @router.get("/{session_id}")
    async def get_session(session_id: str):
        if session_id not in _sessions:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        return _sessions[session_id]

    @router.patch("/{session_id}")
    async def update_session(session_id: str, body: dict):
        if session_id not in _sessions:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        _sessions[session_id].update(body)
        return _sessions[session_id]

    @router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_session(session_id: str):
        if session_id not in _sessions:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        del _sessions[session_id]

    app.include_router(router)
    return app


@pytest.fixture
def client(app_with_sessions: FastAPI) -> TestClient:
    return TestClient(app_with_sessions)


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

class TestSessionCreate:

    def test_create_session_default_title(self, client: TestClient):
        resp = client.post("/api/v1/sessions/", json={"title": "New Chat"})
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["title"] == "New Chat"
        assert "id" in data

    def test_create_session_custom_title(self, client: TestClient):
        resp = client.post("/api/v1/sessions/", json={"title": "Sprint Planning Discussion"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["title"] == "Sprint Planning Discussion"

    def test_create_session_returns_valid_uuid(self, client: TestClient):
        resp = client.post("/api/v1/sessions/", json={"title": "Test"})
        data = resp.json()
        uuid.UUID(data["id"])  # Should not raise


class TestSessionList:

    def test_list_sessions_empty(self, client: TestClient):
        resp = client.get("/api/v1/sessions/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_list_sessions_after_create(self, client: TestClient):
        client.post("/api/v1/sessions/", json={"title": "Session 1"})
        client.post("/api/v1/sessions/", json={"title": "Session 2"})
        resp = client.get("/api/v1/sessions/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 2


class TestSessionGet:

    def test_get_session_exists(self, client: TestClient):
        create_resp = client.post("/api/v1/sessions/", json={"title": "My Session"})
        session_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["title"] == "My Session"

    def test_get_session_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/sessions/{fake_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestSessionUpdate:

    def test_update_session_title(self, client: TestClient):
        create_resp = client.post("/api/v1/sessions/", json={"title": "Old Title"})
        session_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/sessions/{session_id}",
            json={"title": "Updated Title"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["title"] == "Updated Title"

    def test_update_session_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"/api/v1/sessions/{fake_id}", json={"title": "X"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestSessionDelete:

    def test_delete_session(self, client: TestClient):
        create_resp = client.post("/api/v1/sessions/", json={"title": "To Delete"})
        session_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        resp = client.get(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_session_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/sessions/{fake_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
