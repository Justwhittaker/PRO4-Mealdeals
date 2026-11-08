"""Reject website URLs that can reach the local network.

OSM `website` tags are untrusted. Every request checks the scheme, the port,
and the resolved addresses, including each redirect hop. A name that resolves
to a private, loopback, link-local, or reserved address is not fetched.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx

Resolver = Callable[[str], list[str]]

_STANDARD_PORTS = {80, 443}


def _parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    text = host.strip().strip("[]")
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        pass
    if text.isdigit():
        value = int(text)
        if 0 <= value <= 0xFFFFFFFF:
            return ipaddress.ip_address(value)
    # socket.inet_aton accepts shorthand such as 127.1.
    try:
        packed = socket.inet_aton(text)
    except OSError:
        return None
    return ipaddress.ip_address(packed)


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def default_resolver(host: str) -> list[str]:
    """Public addresses for ``host``. Empty when DNS fails or any answer is blocked."""
    literal = _parse_ip(host)
    if literal is not None:
        if _blocked_ip(literal):
            return []
        return [str(literal)]
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return []
    addresses: list[str] = []
    for info in infos:
        raw = info[4][0]
        parsed = _parse_ip(raw)
        if parsed is None or _blocked_ip(parsed):
            return []
        if str(parsed) not in addresses:
            addresses.append(str(parsed))
    return addresses


def url_is_safe(url: str, *, resolve: Resolver = default_resolver) -> bool:
    """True for http(s) on port 80 or 443 whose host resolves only to public IPs."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host or host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return False
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if port not in _STANDARD_PORTS:
        return False
    if parsed.scheme == "http" and port != 80:
        return False
    if parsed.scheme == "https" and port != 443:
        return False
    addresses = resolve(host)
    if not addresses:
        return False
    for address in addresses:
        parsed_ip = _parse_ip(address)
        if parsed_ip is None or _blocked_ip(parsed_ip):
            return False
    return True


def redirect_target(current: str, location: str) -> str:
    return urljoin(current, location)


def pinned_request_url(url: str, ip: str) -> str:
    """Replace the host with ``ip`` so the connection cannot rebind via DNS."""
    parsed = urlparse(url)
    host = ip if ":" not in ip else f"[{ip}]"
    port = ""
    if parsed.port and parsed.port not in {80, 443}:
        port = f":{parsed.port}"
    elif parsed.port in {80, 443} and (
        (parsed.scheme == "http" and parsed.port != 80)
        or (parsed.scheme == "https" and parsed.port != 443)
    ):
        port = f":{parsed.port}"
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return f"{parsed.scheme}://{host}{port}{path}"


class PublicOnlyTransport(httpx.BaseTransport):
    """Connect to a resolved public address and keep the original name for TLS."""

    def __init__(self, resolve: Resolver = default_resolver) -> None:
        self._resolve = resolve
        self._inner = httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if not url_is_safe(str(request.url), resolve=self._resolve):
            raise httpx.ConnectError("blocked url")
        addresses = self._resolve(host)
        if not addresses:
            raise httpx.ConnectError("blocked address")
        pinned = pinned_request_url(str(request.url), addresses[0])
        headers = request.headers.copy()
        headers["host"] = host
        outgoing = httpx.Request(
            request.method,
            pinned,
            headers=headers,
            content=request.content,
            extensions={**dict(request.extensions), "sni_hostname": host},
        )
        return self._inner.handle_request(outgoing)

    def close(self) -> None:
        self._inner.close()
