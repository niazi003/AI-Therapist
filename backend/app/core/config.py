"""Application configuration using Pydantic Settings."""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Personal Wellbeing Companion"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = Field(default="changeme-insecure-default-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "wellbeing"
    POSTGRES_PASSWORD: str = "wellbeing"
    POSTGRES_DB: str = "wellbeing"

    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Synchronous database URL for Alembic."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_CHAT_MODEL: str = "openai/gpt-oss-120b"
    GROQ_SAFETY_MODEL: str = "openai/gpt-oss-20b"
    GROQ_TIMEOUT_SECONDS: int = 30

    # Koko crisis helplines API
    KOKO_HELPLINES_API_URL: str = "https://helpline-api.koko.ai/crisis_helplines"
    KOKO_API_ORIGIN: Optional[str] = None

    # LangGraph
    LANGGRAPH_CONSOLIDATION_INTERVAL: int = Field(default=8, ge=1)
    LANGGRAPH_MAX_CONTEXT_MESSAGES: int = Field(default=20, ge=1)

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()