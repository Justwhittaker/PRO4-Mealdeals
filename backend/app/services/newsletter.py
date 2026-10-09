"""Newsletter subscribe helpers.

Friday Weekly Specials selection, quality filtering, and the email body
live in ``app.services.weekly_specials``. This module re-exports the
send entry point used by the Friday job.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from urllib.parse import quote

from app.core.config import get_settings
from app.models.newsletter import NewsletterSubscriber
from app.services.weekly_specials import send_weekly_special_to_subscriber

__all__ = [
    "new_unsubscribe_token",
    "normalize_email",
    "resubscribe_url",
    "send_weekly_special_to_subscriber",
    "soft_resubscribe",
    "soft_unsubscribe",
    "unsubscribe_url",
]


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


def unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/newsletter/unsubscribe?token={quote(token)}"


def resubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/newsletter?resubscribe=1&token={quote(token)}"


def soft_unsubscribe(subscriber: NewsletterSubscriber) -> None:
    """Mark unsubscribed without deleting the row."""
    subscriber.is_subscribed = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc)


def soft_resubscribe(subscriber: NewsletterSubscriber) -> None:
    subscriber.is_subscribed = True
    subscriber.unsubscribed_at = None
