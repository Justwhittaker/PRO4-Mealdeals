"""Dedupe and normalize scrape sources before deal emission."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.scrapers.hub_radius import hub_default_locality

_CHAIN_NAME_RE = re.compile(
    r"(?i)\b("
    r"mcdonald|burger\s*king|kfc|subway|domino|pizza\s*hut|papa\s*john|"
    r"starbucks|costa|nandos|nando.?s|pret|greggs|wetherspoon|"
    r"marriott|hilton|holiday\s*inn|premier\s*inn|ibis|novotel|"
    r"tesco|sainsbury|aldi|lidl|walmart|carrefour|dunnes|supervalu|"
    r"centra|asda|morrisons|waitrose|chipotle|taco\s*bell|wendy|"
    r"hard\s*rock|olive\s*garden|applebee|ihop|pizza\s*express|"
    r"five\s*guys|tim\s*horton|dunkin"
    r")\b"
)


def source_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_national_chain(merchant: str, source: dict[str, str]) -> bool:
    kind = str(source.get("source_kind") or "")
    if kind in {"local_independent"}:
        return False
    if kind in {"local_chain", "national_chain"}:
        return True
    return bool(_CHAIN_NAME_RE.search(merchant or ""))


def dedupe_chain_sources_for_hub(
    sources: list[dict[str, str]],
    *,
    hub: str,
) -> list[dict[str, str]]:
    """
    One national chain deal per hub (Domino's → main /deals page, hub city label).

    Prevents the same chain appearing as separate deals for Tuam, Oranmore, etc.
    """
    seen_hosts: set[str] = set()
    seen_merchants: set[str] = set()
    hub_title = hub.strip().title()
    hub_local = hub_default_locality(hub_title)
    filtered: list[dict[str, str]] = []

    for source in sources:
        merchant = str(source.get("merchant") or "").strip()
        url = str(source.get("url") or "").strip()
        if not merchant or not url:
            continue
        host = source_host(url)
        merchant_key = merchant.lower()

        if is_national_chain(merchant, source):
            if host in seen_hosts or merchant_key in seen_merchants:
                continue
            seen_hosts.add(host)
            seen_merchants.add(merchant_key)
            row = dict(source)
            row["area_local"] = hub_local
            row["source_kind"] = "national_chain"
            filtered.append(row)
            continue

        if host and host in seen_hosts and merchant_key in seen_merchants:
            continue
        if host:
            seen_hosts.add(host)
        seen_merchants.add(merchant_key)
        filtered.append(dict(source))

    return filtered
