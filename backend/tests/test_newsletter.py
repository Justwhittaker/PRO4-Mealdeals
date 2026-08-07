"""Newsletter soft-unsubscribe keeps the row."""

from __future__ import annotations

from app.services.newsletter import (
    new_unsubscribe_token,
    normalize_email,
    soft_resubscribe,
    soft_unsubscribe,
)
from app.models.newsletter import NewsletterSubscriber


def test_normalize_email() -> None:
    assert normalize_email("  Alex@Example.COM ") == "alex@example.com"


def test_soft_unsubscribe_preserves_identity() -> None:
    sub = NewsletterSubscriber(
        name="Alex",
        email="alex@example.com",
        location="London, UK",
        is_subscribed=True,
        unsubscribe_token=new_unsubscribe_token(),
    )
    soft_unsubscribe(sub)
    assert sub.is_subscribed is False
    assert sub.unsubscribed_at is not None
    assert sub.email == "alex@example.com"
    assert sub.name == "Alex"
    soft_resubscribe(sub)
    assert sub.is_subscribed is True
    assert sub.unsubscribed_at is None
