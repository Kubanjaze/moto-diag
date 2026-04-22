"""Application configuration using pydantic-settings."""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root is 3 levels up from this file: src/motodiag/core/config.py → moto-diag/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


class Environment(str, Enum):
    """Application environment profiles."""
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


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
    env: Environment = Environment.DEV

    # Paths
    data_dir: str = str(DATA_DIR)
    output_dir: str = str(OUTPUT_DIR)
    db_path: str = str(DATA_DIR / "motodiag.db")

    # AI Engine
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048
    ai_temperature: float = 0.3

    # Hardware
    serial_port: str = ""
    baud_rate: int = 9600
    connection_timeout: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # API (Phase 175+)
    api_host: str = "127.0.0.1"
    api_port: int = 8080
    api_cors_origins: str = (
        "http://localhost:3000,http://localhost:5173"
    )
    api_log_level: str = "INFO"

    @property
    def api_cors_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a clean list."""
        raw = (self.api_cors_origins or "").strip()
        if not raw:
            return []
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Billing (Phase 176+)
    billing_provider: str = "fake"  # "fake" | "stripe"
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_individual: str = ""
    stripe_price_shop: str = ""
    stripe_price_company: str = ""
    checkout_success_url: str = "http://localhost:3000/billing/success"
    checkout_cancel_url: str = "http://localhost:3000/billing/cancel"
    billing_portal_return_url: str = "http://localhost:3000/billing"

    # Rate limiting (Phase 176+)
    rate_limit_anonymous_per_minute: int = 30
    rate_limit_individual_per_minute: int = 60
    rate_limit_shop_per_minute: int = 300
    rate_limit_company_per_minute: int = 1000
    rate_limit_anonymous_per_day: int = 100
    rate_limit_individual_per_day: int = 1000
    rate_limit_shop_per_day: int = 10000
    rate_limit_company_per_day: int = 50000

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 100 or v > 8192:
            raise ValueError("max_tokens must be between 100 and 8192")
        return v

    @field_validator("ai_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("ai_temperature must be between 0.0 and 1.0")
        return v

    @field_validator("baud_rate")
    @classmethod
    def validate_baud_rate(cls, v: int) -> int:
        valid = {9600, 19200, 38400, 57600, 115200}
        if v not in valid:
            raise ValueError(f"baud_rate must be one of {valid}")
        return v

    def get_data_path(self, *parts: str) -> Path:
        """Get a path relative to the data directory."""
        return Path(self.data_dir).joinpath(*parts)

    def get_output_path(self, *parts: str) -> Path:
        """Get a path relative to the output directory."""
        return Path(self.output_dir).joinpath(*parts)


def ensure_directories(settings: Optional[Settings] = None) -> dict[str, bool]:
    """Create required data directories if they don't exist. Returns created status."""
    if settings is None:
        settings = get_settings()

    dirs = {
        "data": Path(settings.data_dir),
        "data/dtc_codes": Path(settings.data_dir) / "dtc_codes",
        "data/vehicles": Path(settings.data_dir) / "vehicles",
        "data/knowledge": Path(settings.data_dir) / "knowledge",
        "output": Path(settings.output_dir),
    }

    results = {}
    for name, path in dirs.items():
        existed = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        results[name] = not existed  # True if newly created
    return results


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    return Settings()


def reset_settings() -> Settings:
    """Clear cached settings and return fresh instance. Useful for testing."""
    get_settings.cache_clear()
    return get_settings()
