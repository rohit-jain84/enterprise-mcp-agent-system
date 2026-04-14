"""FastAPI dependency injection helpers."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings as _get_settings
from app.db.engine import get_async_session
from app.models.database import User

logger = logging.getLogger(__name__)


# ---------- Settings ----------

def get_settings() -> Settings:
    return _get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------- Database Session ----------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session from the shared factory."""
    async for session in get_async_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ---------- Current User (JWT) ----------

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Decode JWT from the Authorization header and return the corresponding User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if authorization is None:
        raise credentials_exception

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise credentials_exception from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
