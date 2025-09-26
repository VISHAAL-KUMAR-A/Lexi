"""Configuration module for the Lexi FastAPI application."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="Lexi Case Search API",
                          description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")
    version: str = Field(default="1.0.0", description="API version")

    # Jagriti API settings
    jagriti_base_url: str = Field(
        default="https://e-jagriti.gov.in",
        description="Base URL for Jagriti API",
        alias="JAGRITI_BASE_URL",
    )
    jagriti_timeout: int = Field(
        default=30,
        description="Timeout for Jagriti API requests in seconds",
        alias="JAGRITI_TIMEOUT",
    )
    jagriti_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for Jagriti API requests",
        alias="JAGRITI_MAX_RETRIES",
    )

    # Cache settings
    cache_ttl_states: int = Field(
        default=86400,  # 24 hours
        description="Cache TTL for states data in seconds",
        alias="CACHE_TTL_STATES",
    )
    cache_ttl_commissions: int = Field(
        default=86400,  # 24 hours
        description="Cache TTL for commissions data in seconds",
        alias="CACHE_TTL_COMMISSIONS",
    )

    # API settings
    default_page_size: int = Field(
        default=20,
        description="Default page size for paginated responses",
        alias="DEFAULT_PAGE_SIZE",
    )
    max_page_size: int = Field(
        default=100,
        description="Maximum allowed page size",
        alias="MAX_PAGE_SIZE",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        alias="LOG_LEVEL",
    )

    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
        alias="HOST",
    )
    port: int = Field(
        default=8000,
        description="Server port",
        alias="PORT",
    )

    # Jagriti client security and robustness settings
    allow_captcha_solver: bool = Field(
        default=False,
        description="Allow captcha solver service integration (placeholder)",
        alias="ALLOW_CAPTCHA_SOLVER",
    )
    jagriti_concurrent_limit: int = Field(
        default=5,
        description="Maximum concurrent requests to Jagriti",
        alias="JAGRITI_CONCURRENT_LIMIT",
    )
    jagriti_request_delay_min: float = Field(
        default=0.05,  # 50ms
        description="Minimum delay between requests (seconds)",
        alias="JAGRITI_REQUEST_DELAY_MIN",
    )
    jagriti_request_delay_max: float = Field(
        default=0.3,  # 300ms
        description="Maximum delay between requests (seconds)",
        alias="JAGRITI_REQUEST_DELAY_MAX",
    )
    jagriti_retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff factor for retries",
        alias="JAGRITI_RETRY_BACKOFF_FACTOR",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
