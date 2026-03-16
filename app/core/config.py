"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Legal Radar"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/legal_radar"

    # AI
    DEEPSEEK_KEY: str = ""
    GROK_XAI_KEY: str = ""

    # API server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Dashboard
    DASH_HOST: str = "0.0.0.0"
    DASH_PORT: int = 8050

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous DB URL for migrations (psycopg2)."""
        return self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
