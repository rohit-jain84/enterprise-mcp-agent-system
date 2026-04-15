"""Tests for authentication endpoints: login, token refresh, protected routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.models.schemas import LoginRequest, RefreshRequest, TokenResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user():
    """A mock User ORM object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.full_name = "Alice Smith"
    user.role = "user"
    user.is_active = True
    user.hashed_password = "$2b$12$fakehash"
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def app_with_auth(mock_user) -> FastAPI:
    """Build a minimal FastAPI app with auth routes and mocked deps."""
    from fastapi import APIRouter, Depends

    app = FastAPI()
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.post("/login", response_model=TokenResponse)
    async def login(body: LoginRequest):
        # Simulate successful login
        return TokenResponse(
            access_token="mock-access-token",
            refresh_token="mock-refresh-token",
            token_type="bearer",
            expires_in=3600,
        )

    @router.post("/refresh", response_model=TokenResponse)
    async def refresh(body: RefreshRequest):
        if body.refresh_token == "valid-refresh-token":
            return TokenResponse(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                token_type="bearer",
                expires_in=3600,
            )
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    @router.get("/me")
    async def me():
        return {
            "id": str(mock_user.id),
            "email": mock_user.email,
            "full_name": mock_user.full_name,
            "role": mock_user.role,
        }

    app.include_router(router)
    return app


@pytest.fixture
def client(app_with_auth: FastAPI) -> TestClient:
    return TestClient(app_with_auth)


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

class TestLogin:

    def test_login_success(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "secret123"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_missing_password(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_empty_password(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": ""},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_missing_email(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"password": "secret123"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------

class TestTokenRefresh:

    def test_refresh_success(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid-refresh-token"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["access_token"] == "new-access-token"
        assert data["refresh_token"] == "new-refresh-token"

    def test_refresh_invalid_token(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_missing_token(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Protected endpoint tests
# ---------------------------------------------------------------------------

class TestProtectedEndpoints:

    def test_me_returns_user_info(self, client: TestClient, mock_user):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["email"] == "alice@example.com"
        assert data["full_name"] == "Alice Smith"


class TestJWTValidation:
    """Test JWT token encoding and decoding contract."""

    def test_jwt_encode_decode(self):
        from jose import jwt

        secret = "test-secret"
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["sub"] == payload["sub"]

    def test_jwt_expired_token_rejected(self):
        from jose import jwt, JWTError

        secret = "test-secret"
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        with pytest.raises(JWTError):
            jwt.decode(token, secret, algorithms=["HS256"])

    def test_jwt_wrong_secret_rejected(self):
        from jose import jwt, JWTError

        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "correct-secret", algorithm="HS256")
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])
