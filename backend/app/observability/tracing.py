"""LangSmith tracing configuration."""

from __future__ import annotations

import logging
import os

from app.config import get_settings

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Set LangSmith environment variables if tracing is enabled.

    LangChain libraries automatically pick up these env vars, so we just
    need to ensure they are present in ``os.environ``.
    """
    settings = get_settings()

    if not settings.LANGCHAIN_TRACING_V2:
        logger.info("LangSmith tracing is disabled")
        return

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.LANGCHAIN_ENDPOINT)

    logger.info(
        "LangSmith tracing enabled -- project=%s endpoint=%s",
        settings.LANGCHAIN_PROJECT,
        settings.LANGCHAIN_ENDPOINT,
    )


def disable_tracing() -> None:
    """Explicitly disable LangSmith tracing."""
    os.environ.pop("LANGCHAIN_TRACING_V2", None)
    logger.info("LangSmith tracing disabled")
