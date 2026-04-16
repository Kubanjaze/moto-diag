"""Application configuration using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root is 3 levels up from this file: src/motodiag/core/config.py → moto-diag/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


class Settings(BaseSettings):
    """Global application settings, loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="MOTODIAG_",
        extra="ignore",
    )

    # General
    app_name: str = "motodiag"
    version: str = "0.1.0"
    debug: bool = False

    # Database
    db_path: str = str(PROJECT_ROOT / "data" / "motodiag.db")

    # AI Engine
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048

    # Hardware
    serial_port: str = ""
    baud_rate: int = 9600


def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    return Settings()
