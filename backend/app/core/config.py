"""Application configuration via environment variables.

Required configuration is validated eagerly at import/startup time so that a
badly-configured deployment fails loudly rather than silently misbehaving.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Core ---
    APP_NAME: str = "SmartSupport AI"
    ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://smartuser:smartpass@localhost:5432/smartsupport"

    # --- Redis (optional; app degrades gracefully when unavailable) ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    # --- Security ---
    # Must be set in production. Auto-generated only for local dev convenience.
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    ALGORITHM: str = "HS256"
    COOKIE_SECURE: bool = False

    # --- CORS ---
    # Stored as a raw string; parsed into a list by the property below so that
    # both .env ("a,b") and direct kwargs (list) work without JSON-decoding.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Rate limiting ---
    # In-memory sliding-window rate limiter (see core.ratelimit). Auto-disabled
    # in the test environment so the suite isn't throttled; override explicitly
    # when needed. Defaults on for development/staging/production.
    RATE_LIMIT_ENABLED: bool = True

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- AI ---
    AI_ENABLED: bool = True
    AI_PROVIDER: str = "openai_compat"
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_CHAT_MODEL: str = "gpt-4o-mini"
    AI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_EMBEDDING_DIM: int = 1536
    AI_REQUEST_TIMEOUT_SECONDS: int = 60
    AI_MAX_RETRIES: int = 2
    AI_MIN_CONFIDENCE: float = 0.45  # below this, classification routes to human review

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:5173"

    # --- Seed admin ---
    SEED_ADMIN_EMAIL: str = "admin@smart.support"
    SEED_ADMIN_PASSWORD: str = "admin123"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _validate(settings)
    return settings


def _validate(settings: Settings) -> None:
    """Fail fast if required configuration is missing or obviously wrong."""
    if settings.ENV not in {"development", "test", "staging", "production"}:
        raise RuntimeError(f"Invalid ENV value: {settings.ENV!r}")

    if settings.ENV == "production":
        if settings.SECRET_KEY == "dev-insecure-secret-change-me":
            raise RuntimeError(
                "SECRET_KEY must be set to a strong value in production."
            )
        if settings.AI_ENABLED and not settings.AI_API_KEY:
            raise RuntimeError(
                "AI_ENABLED is true but AI_API_KEY is missing."
            )
        if "localhost" in settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL points at localhost; production must use a real host."
            )
