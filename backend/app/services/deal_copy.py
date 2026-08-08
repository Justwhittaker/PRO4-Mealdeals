"""Sanitize user-facing deal copy (strip legacy scrape boilerplate)."""

from __future__ import annotations

import re

_SCRAPE_PHRASES = (
    re.compile(r"\s*External scraped listing\.?", re.IGNORECASE),
    re.compile(r"\s*Scraped external deal\s*[—-]?\s*", re.IGNORECASE),
    re.compile(r"\s*External listing\s*[—-]?\s*", re.IGNORECASE),
)


def clean_deal_description(value: str | None) -> str | None:
    if not value:
        return value
    text = value
    for pattern in _SCRAPE_PHRASES:
        text = pattern.sub(" ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([.!?])", r"\1", text)
    text = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", text)
    text = text.strip(" —-\t")
    return text or None
