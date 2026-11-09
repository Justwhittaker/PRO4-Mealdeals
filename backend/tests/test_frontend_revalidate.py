"""Vercel checkpoint responses must not be logged as an HTML dump."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import httpx
import pytest

from app.services.frontend_revalidate import (
    is_vercel_security_checkpoint,
    revalidate_after_scrape,
)
from app.services.scrape_runner import _live_revalidate

_SECRET = "revalidate-secret-value"
_REDIS = "redis://default:pw@10.1.1.1:6379/0"
_CHECKPOINT_HTML = (
    "<!DOCTYPE html><html><head><title>Vercel Security Checkpoint</title></head>"
    "<body>"
    + (_SECRET + " " + _REDIS + " ")
    + ("checkpoint " * 400)
    + "</body></html>"
)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        revalidate_secret=_SECRET,
        frontend_base_url="https://dineadeal.com",
    )


def _install_client(monkeypatch: pytest.MonkeyPatch, response: httpx.Response | Exception) -> dict:
    posted: dict[str, object] = {}

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def post(self, url: str, json: dict | None = None) -> httpx.Response:
            posted["url"] = url
            posted["json"] = json
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr("app.services.frontend_revalidate.httpx.Client", _Client)
    monkeypatch.setattr("app.services.frontend_revalidate.get_settings", _settings)
    return posted


def test_checkpoint_markers() -> None:
    challenged = httpx.Response(
        429,
        headers={"X-Vercel-Mitigated": "challenge"},
        text="no title here",
    )
    titled = httpx.Response(429, text=_CHECKPOINT_HTML)
    plain = httpx.Response(429, text="Too Many Requests")
    denied = httpx.Response(
        429,
        headers={"x-vercel-mitigated": "deny"},
        text="blocked",
    )
    wrong_status = httpx.Response(
        403,
        headers={"x-vercel-mitigated": "challenge"},
        text=_CHECKPOINT_HTML,
    )
    assert is_vercel_security_checkpoint(challenged) is True
    assert is_vercel_security_checkpoint(titled) is True
    assert is_vercel_security_checkpoint(plain) is False
    assert is_vercel_security_checkpoint(denied) is False
    assert is_vercel_security_checkpoint(wrong_status) is False


def test_challenge_revalidate_logs_a_short_line(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    posted = _install_client(
        monkeypatch,
        httpx.Response(
            429,
            headers={"x-vercel-mitigated": "challenge"},
            text=_CHECKPOINT_HTML,
        ),
    )
    with caplog.at_level(logging.WARNING, logger="app.services.frontend_revalidate"):
        result = revalidate_after_scrape(areas={("IE", "Dublin")})

    assert result["ok"] is False
    assert result["challenge"] is True
    assert result["status"] == 429
    assert result["detail"] == "Vercel challenge (429)"
    assert "Vercel challenge (429)" in caplog.text
    assert "<!DOCTYPE" not in caplog.text
    assert "Vercel Security Checkpoint" not in caplog.text
    assert _SECRET not in caplog.text
    assert "redis://" not in caplog.text
    assert _SECRET not in str(result)
    sent = posted["json"]
    assert isinstance(sent, dict)
    assert sent["secret"] == _SECRET


def test_other_revalidate_errors_are_truncated_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = (
        f"<!DOCTYPE html>{_SECRET} {_REDIS} "
        + ("<p>gateway</p>" * 200)
    )
    _install_client(monkeypatch, httpx.Response(503, text=page))
    with caplog.at_level(logging.WARNING, logger="app.services.frontend_revalidate"):
        result = revalidate_after_scrape(areas={("IE", "Dublin")})

    assert result["ok"] is False
    assert result.get("challenge") is not True
    assert result["status"] == 503
    assert _SECRET not in result["detail"]
    assert "redis://" not in result["detail"]
    assert "[redacted]" in result["detail"]
    assert len(result["detail"]) <= 181
    assert _SECRET not in caplog.text
    assert "redis://" not in caplog.text
    assert "Frontend revalidate failed (503):" in caplog.text
    assert page not in caplog.text


def test_revalidate_request_errors_do_not_log_secrets(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_client(
        monkeypatch,
        httpx.ConnectError(f"connect failed {_SECRET} {_REDIS}"),
    )
    with caplog.at_level(logging.WARNING, logger="app.services.frontend_revalidate"):
        result = revalidate_after_scrape(areas={("IE", "Dublin")})

    assert result["ok"] is False
    assert "challenge" not in result
    assert _SECRET not in result["error"]
    assert "redis://" not in result["error"]
    assert _SECRET not in caplog.text
    assert "redis://" not in caplog.text
    assert "Frontend revalidate request failed:" in caplog.text


def test_auth_failure_is_not_a_challenge(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_client(
        monkeypatch,
        httpx.Response(401, json={"error": "Unauthorized"}),
    )
    with caplog.at_level(logging.WARNING, logger="app.services.frontend_revalidate"):
        result = revalidate_after_scrape(areas={("IE", "Dublin")})

    assert result["ok"] is False
    assert result["status"] == 401
    assert result.get("challenge") is not True
    assert "Unauthorized" in result["detail"]
    assert "Vercel challenge" not in caplog.text


def test_city_revalidate_log_does_not_dump_the_checkpoint_page(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "app.services.scrape_runner.revalidate_after_scrape",
        lambda **_kwargs: {
            "ok": False,
            "status": 429,
            "challenge": True,
            "detail": _CHECKPOINT_HTML,
        },
    )
    with caplog.at_level(logging.INFO, logger="app.services.scrape_runner"):
        result = _live_revalidate("IE", "Dublin", ingested=1, stale=0)

    assert result["challenge"] is True
    assert "Vercel challenge (429)" in caplog.text
    assert "<!DOCTYPE" not in caplog.text
    assert _SECRET not in caplog.text
    assert "redis://" not in caplog.text
