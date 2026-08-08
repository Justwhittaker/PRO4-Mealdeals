"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

_DEFAULT_SYNC_URL = "postgresql://mealdeals:mealdeals@localhost:5432/mealdeals"
_DEFAULT_ASYNC_URL = "postgresql+asyncpg://mealdeals:mealdeals@localhost:5432/mealdeals"


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _to_sync_url(url: str) -> str:
    if "+asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _with_sslmode(url: str) -> str:
    """Require TLS for Render's public Postgres hostnames."""
    if "render.com" not in url:
        return url
    if "sslmode=" in url or "ssl=" in url:
        return url
    return f"{url}&sslmode=require" if "?" in url else f"{url}?sslmode=require"


class Settings(BaseSettings):
    """Runtime configuration for the Dine A Deal API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Dine A Deal API"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-production", min_length=8)

    # Bind host/port (Render / Docker expect 0.0.0.0:$PORT)
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = _DEFAULT_ASYNC_URL
    database_url_sync: str = _DEFAULT_SYNC_URL

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Affiliate network tags (env-configurable)
    amazon_associate_tag: str = "mealdeals-20"
    booking_aid: str = "000000"
    awin_publisher_id: str = "000000"
    cj_website_id: str = "000000"
    impact_campaign_id: str = "000000"
    rakuten_mid: str = "000000"

    # Currency cache TTL (seconds)
    currency_cache_ttl: int = 3600

    # Click log TTL in Redis (seconds)
    click_log_ttl: int = 86400 * 7

    # CORS origins as comma-separated string (avoids pydantic-settings list JSON decode).
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )

    # Shared secret for design fulfill + inbound email auto-post
    design_fulfill_secret: str = Field(default="mealdeals-design")

    # Public site URL (unsubscribe / deal links in emails)
    frontend_base_url: str = Field(default="https://dineadeal.com")

    # Resend HTTPS API (preferred on Render free — SMTP ports are blocked there)
    resend_api_key: str = Field(default="")
    resend_from_email: str = Field(
        default="Dine A Deal <onboarding@resend.dev>"
    )

    # SMTP fallback (local/dev, or paid Render with SMTP_ALLOW=true)
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@dineadeal.com")
    smtp_use_tls: bool = Field(default=True)
    # Render free blocks 25/465/587 — keep false in production unless on a paid instance.
    smtp_allow: bool = Field(default=False)

    # Inbox for public contact form submissions
    contact_to_email: str = Field(default="just.whittaker@gmail.com")

    @model_validator(mode="after")
    def normalize_database_urls(self) -> Self:
        """Accept Render's postgresql:// DATABASE_URL and derive async/sync forms."""
        raw_async = self.database_url.strip()
        raw_sync = self.database_url_sync.strip()

        # Prefer an explicitly provided sync URL; otherwise derive from DATABASE_URL.
        if raw_sync == _DEFAULT_SYNC_URL and raw_async not in {
            _DEFAULT_ASYNC_URL,
            _DEFAULT_SYNC_URL,
        }:
            raw_sync = _to_sync_url(raw_async)
        elif raw_async == _DEFAULT_ASYNC_URL and raw_sync != _DEFAULT_SYNC_URL:
            raw_async = raw_sync

        sync_url = _to_sync_url(raw_sync)
        async_base = _to_asyncpg_url(_to_sync_url(raw_async))
        self.database_url_sync = _with_sslmode(sync_url)
        # asyncpg SSL is handled via connect_args — keep query params out of the URL.
        self.database_url = async_base.split("?", 1)[0]
        return self

    @property
    def database_requires_ssl(self) -> bool:
        return "render.com" in self.database_url_sync or "render.com" in self.database_url

    @property
    def cors_origin_list(self) -> List[str]:
        stripped = self.cors_origins.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [item.strip() for item in stripped.split(",") if item.strip()]

    @property
    def cors_allow_credentials(self) -> bool:
        return self.cors_origin_list != ["*"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
