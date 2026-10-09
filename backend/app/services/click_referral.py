"""Validate newsletter referral tags stored on click_events."""

from __future__ import annotations

import re

_UTM_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def clean_utm(value: str | None) -> str | None:
    """Keep a single utm token. Reject URLs and other free-form values."""
    if value is None:
        return None
    text = value.strip()
    if not text or _UTM_RE.match(text) is None:
        return None
    return text
