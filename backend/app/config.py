"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object -- all values come from env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://agent:agent_dev@localhost:5432/agent_db"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # --- OpenAI ---
    OPENAI_API_KEY: str = ""

    # --- MCP Server URLs ---
    GITHUB_MCP_URL: str = "http://localhost:8001"
    PROJECT_MGMT_MCP_URL: str = "http://localhost:8002"
    CALENDAR_MCP_URL: str = "http://localhost:8003"

    # --- LangChain / LangSmith ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "enterprise-mcp-agent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # --- Guardrails ---
    GUARDRAILS_ENABLED: bool = True

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- Cost Budget ---
    COST_BUDGET_PER_USER_DAILY: float = 5.0   # max dollars per user per day
    COST_BUDGET_PER_SESSION: float = 1.0       # max dollars per session

    # --- App ---
    APP_NAME: str = "Enterprise MCP Agent System"
    DEBUG: bool = False


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
