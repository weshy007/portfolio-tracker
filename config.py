"""Configuration management for Portfolio Tracker."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Portfolio Tracker"
    app_env: str = "development"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./app.db"

    # Currency API
    currency_api_url: str = "https://api.exchangerate-api.com/v4/latest"
    currency_api_key: str = ""
    currency_cache_minutes: int = 60
    mansa_api_key: str = ""
    mansa_api_url: str = "https://mansaapi.com/api/v1"
    pesacalc_mmf_url: str = "https://pesacalc.co.ke/calculators/money-market"

    # Default currency
    default_currency: str = "KES"

    # CORS
    cors_origins: list[str] = ["*"]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1"]

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> bool:
        """Treat deployment labels such as `release` as debug disabled."""
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "debug"}
        return bool(value)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"


settings = Settings()
