"""Keep HTTP client libraries from logging every request at INFO."""

from __future__ import annotations

import logging

_HTTP_CLIENT_LOGGERS = ("httpx", "httpcore")


def quiet_http_client_logs() -> None:
    """Drop per-request httpx/httpcore INFO lines. Warnings and errors stay."""
    for name in _HTTP_CLIENT_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
