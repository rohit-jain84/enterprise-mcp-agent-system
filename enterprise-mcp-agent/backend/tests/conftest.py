"""Pytest fixtures for async test client, test DB, etc."""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.auth import hash_password
from app.config import Settings
from app.dependencies import get_current_user, get_db, get_settings
from app.models.database import Base, User


# ---------- Settings override ----------

def _test_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        REDIS_URL="redis://localhost:6379/15",
        JWT_SECRET_KEY="test-secret-key",
        ANTHROPIC_API_KEY="test-key",
        LANGCHAIN_TRACING_V2=False,
        GUARDRAILS_ENABLED=False,
        DEBUG=True,
    )


# ---------- Engine & session for tests ----------

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    echo=False,
)

_test_session_factory = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables before tests, drop after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional DB session that rolls back after each test."""
    async with _test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Insert and return a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=hash_password("testpassword"),
        full_name="Test User",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def app(db_session: AsyncSession, test_user: User) -> FastAPI:
    """Build a FastAPI app with dependency overrides for testing."""
    from app.main import create_app

    application = create_app()

    async def _override_db():
        yield db_session

    async def _override_user():
        return test_user

    application.dependency_overrides[get_db] = _override_db
    application.dependency_overrides[get_current_user] = _override_user
    application.dependency_overrides[get_settings] = _test_settings

    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
