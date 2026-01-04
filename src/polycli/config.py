"""Configuration management for PolyCLI."""

from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="POLYCLI_",
    )

    # Polymarket API
    polymarket_api_key: Optional[SecretStr] = Field(default=None)
    polymarket_api_secret: Optional[SecretStr] = Field(default=None)
    polymarket_passphrase: Optional[SecretStr] = Field(default=None)

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///polycli.db")

    # External APIs
    twitter_bearer_token: Optional[SecretStr] = Field(default=None)
    metaculus_api_key: Optional[SecretStr] = Field(default=None)
    manifold_api_key: Optional[SecretStr] = Field(default=None)

    # Trading defaults
    default_kelly_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    reserve_percentage: float = Field(default=0.35, ge=0.0, le=1.0)
    max_position_correlation: float = Field(default=0.7, ge=0.0, le=1.0)

    # Alert settings
    telegram_bot_token: Optional[SecretStr] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[SecretStr] = Field(default=None)

    # Data directory
    data_dir: Path = Field(default=Path.home() / ".polycli")

    def ensure_data_dir(self) -> Path:
        """Ensure data directory exists and return it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
