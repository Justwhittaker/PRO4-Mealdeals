"""Join and parse scraped hrefs without raising on malformed IPv6-like URLs.

Python's ``urllib.parse.urljoin`` / ``urlparse`` raise ``ValueError`` for
bracketed hosts that are not real IPv6 addresses, for example
``http://[invalid`` (``Invalid IPv6 URL``) and
``//[elementor-template%20id=2073]`` (``does not appear to be an IPv4 or IPv6
address``). Those strings show up as hrefs on broken Elementor / parked pages.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse


def safe_urljoin(base: str, href: str) -> str | None:
    """Return an absolute URL, or None when the href cannot be joined."""
    if href is None:
        return None
    raw = str(href).strip()
    if not raw:
        return None
    try:
        joined = urljoin(base, raw)
    except ValueError:
        return None
    if not joined:
        return None
    return joined


def safe_netloc(url: str) -> str:
    """Hostname (and port) or an empty string when the URL cannot be parsed."""
    try:
        return urlparse(url).netloc
    except ValueError:
        return ""
