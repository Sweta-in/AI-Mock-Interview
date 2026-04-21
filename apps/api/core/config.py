"""
PrepAI — Application Configuration
Pydantic v2 settings with environment variable loading.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """All application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "PrepAI"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    SECRET_KEY: str = Field(default="change-me-in-production-32chars!")
    DEBUG: bool = Field(default=True)
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")

    # ── Supabase ─────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(default="")
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")
    SUPABASE_SERVICE_KEY: str = Field(default="")

    # ── PostgreSQL (Supabase) ────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/prepai"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/prepai"
    )

    # ── MongoDB Atlas ────────────────────────────────────────────────────
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="prepai")

    # ── Redis (Upstash) ─────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    UPSTASH_REDIS_REST_URL: str = Field(default="")
    UPSTASH_REDIS_REST_TOKEN: str = Field(default="")

    # ── AI / LLM ─────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    PRIMARY_MODEL: str = Field(default="anthropic/claude-sonnet-4-20250514")
    FALLBACK_MODEL: str = Field(default="openai/gpt-4o-mini")
    LLM_MAX_RETRIES: int = Field(default=2)
    LLM_TIMEOUT_SECONDS: float = Field(default=8.0)

    # ── Celery ───────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_FREE: int = Field(default=100)   # requests per hour
    RATE_LIMIT_PRO: int = Field(default=500)    # requests per hour

    # ── Plan Limits ──────────────────────────────────────────────────────
    FREE_PLAN_INTERVIEW_LIMIT: int = Field(default=3)

    # ── Email (Resend) ───────────────────────────────────────────────────
    RESEND_API_KEY: str = Field(default="")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
