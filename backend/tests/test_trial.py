"""Trial abuse normalization helpers."""

from __future__ import annotations

from app.services.trial import normalize_business_name, normalize_email


def test_normalize_email() -> None:
    assert normalize_email("  Foo@Bar.COM ") == "foo@bar.com"


def test_normalize_business_name() -> None:
    assert normalize_business_name("Joe's Pizza!!!") == "joe s pizza"
    assert normalize_business_name("  ACME   Bistro ") == "acme bistro"
