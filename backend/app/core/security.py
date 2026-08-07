"""Security helpers (API keys, hashing stubs for future auth)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def hash_value(value: str) -> str:
    """Return a SHA-256 hex digest of the given value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


async def verify_optional_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Optional[str]:
    """
    Optional API key gate for admin-style endpoints.

    In development any key (or none) is accepted. In production a matching
    secret_key-derived hash would be enforced — kept intentionally light for
    the MVP bootstrap.
    """
    settings = get_settings()
    if settings.app_env == "development" or settings.app_env == "test":
        return x_api_key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    return x_api_key
