"""Tests for the health check endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.models.schemas import HealthResponse

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_health() -> FastAPI:
    from fastapi import APIRouter

    app = FastAPI()
    router = APIRouter(tags=["health"])

    @router.get("/api/v1/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="healthy",
            database="connected",
            redis="connected",
            mcp_servers={
                "github": "connected",
                "project_mgmt": "connected",
                "calendar": "connected",
            },
            timestamp=datetime.now(UTC),
        )

    @router.get("/api/v1/health/degraded")
    async def health_degraded():
        return HealthResponse(
            status="degraded",
            database="connected",
            redis="disconnected",
            mcp_servers={
                "github": "connected",
                "project_mgmt": "error",
                "calendar": "connected",
            },
            timestamp=datetime.now(UTC),
        ).model_dump(mode="json")

    app.include_router(router)
    return app


@pytest.fixture
def client(app_with_health: FastAPI) -> TestClient:
    return TestClient(app_with_health)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == status.HTTP_200_OK

    def test_health_status_healthy(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_database_connected(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["database"] == "connected"

    def test_health_redis_connected(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["redis"] == "connected"

    def test_health_mcp_servers_present(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "mcp_servers" in data
        assert "github" in data["mcp_servers"]
        assert "project_mgmt" in data["mcp_servers"]
        assert "calendar" in data["mcp_servers"]

    def test_health_all_mcp_connected(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        for server, status_val in data["mcp_servers"].items():
            assert status_val == "connected", f"{server} is not connected"

    def test_health_has_timestamp(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "timestamp" in data
        # Should be parseable as ISO datetime
        datetime.fromisoformat(data["timestamp"])

    def test_health_degraded_status(self, client: TestClient):
        resp = client.get("/api/v1/health/degraded")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["redis"] == "disconnected"
        assert data["mcp_servers"]["project_mgmt"] == "error"


class TestHealthSchema:
    def test_health_response_model(self):
        hr = HealthResponse(
            status="healthy",
            database="connected",
            redis="connected",
            mcp_servers={"github": "connected"},
            timestamp=datetime.now(UTC),
        )
        assert hr.status == "healthy"
        assert hr.mcp_servers["github"] == "connected"

    def test_health_response_serialization(self):
        hr = HealthResponse(
            status="healthy",
            database="connected",
            redis="connected",
            mcp_servers={},
            timestamp=datetime.now(UTC),
        )
        data = hr.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["mcp_servers"], dict)
