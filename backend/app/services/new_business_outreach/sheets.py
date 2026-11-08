"""Weekly Google Sheet export of new leads.

No-op when ``GOOGLE_SERVICE_ACCOUNT_JSON`` is unset or neither a spreadsheet
id nor a Drive folder id is set. Credentials are never logged.

``NEW_BUSINESS_OUTREACH_SHEET_ID`` adds a tab named for the week.
``NEW_BUSINESS_OUTREACH_DRIVE_FOLDER_ID`` creates a new spreadsheet in that
folder when no sheet id is set. If both are set, the sheet id wins.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import google.auth.transport.requests
import httpx
from google.oauth2 import service_account

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal

logger = logging.getLogger(__name__)

SHEET_HEADERS: tuple[str, ...] = (
    "name",
    "type",
    "country",
    "region",
    "address",
    "website",
    "email",
    "source",
    "found date",
)
_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)
_SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
_DRIVE = "https://www.googleapis.com/drive/v3/files"

Request = Callable[..., dict[str, Any]]


def sheet_values(rows: list[dict[str, str]]) -> list[list[str]]:
    """Header plus lean columns. HTML and JSON blobs are not columns."""
    body = [list(SHEET_HEADERS)]
    for row in rows:
        body.append([str(row.get(column) or "") for column in (
            "name",
            "type",
            "country",
            "region",
            "address",
            "website",
            "email",
            "source",
            "found date",
        )])
    return body


def _tab_title(week_label: str) -> str:
    cleaned = re.sub(r"[\[\]\*?:/\\]", " ", week_label).strip()
    return (cleaned or "leads")[:90]


def _load_account(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("{"):
        payload = json.loads(text)
    else:
        payload = json.loads(Path(text).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "client_email" not in payload:
        raise ValueError("service account json missing client_email")
    return payload


def _range_url(spreadsheet_id: str, range_name: str, suffix: str = "") -> str:
    encoded = quote(range_name, safe="")
    return f"{_SHEETS}/{spreadsheet_id}/values/{encoded}{suffix}"


def _access_token(info: dict[str, Any]) -> str:
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=_SCOPES,
    )
    credentials.refresh(google.auth.transport.requests.Request())
    token = credentials.token
    if not token:
        raise RuntimeError("empty access token")
    return str(token)


def _http_request(token: str) -> Request:
    def request(method: str, url: str, *, json_body: dict | list | None = None, params: dict | None = None) -> dict[str, Any]:
        response = httpx.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=json_body,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        payload = response.json()
        return payload if isinstance(payload, dict) else {"values": payload}

    return request


def _write_values(request: Request, spreadsheet_id: str, tab: str, rows: list[dict[str, str]]) -> None:
    range_name = f"'{tab}'!A1"
    request(
        "PUT",
        _range_url(spreadsheet_id, range_name),
        params={"valueInputOption": "RAW"},
        json_body={"range": range_name, "majorDimension": "ROWS", "values": sheet_values(rows)},
    )


def _ensure_tab(request: Request, spreadsheet_id: str, tab: str) -> None:
    meta = request(
        "GET",
        f"{_SHEETS}/{spreadsheet_id}",
        params={"fields": "sheets.properties.title"},
    )
    titles = [
        str((sheet.get("properties") or {}).get("title") or "")
        for sheet in meta.get("sheets") or []
    ]
    if tab in titles:
        request("POST", _range_url(spreadsheet_id, f"'{tab}'!A:Z", ":clear"))
        return
    request(
        "POST",
        f"{_SHEETS}/{spreadsheet_id}:batchUpdate",
        json_body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
    )


def _create_in_folder(request: Request, folder_id: str, title: str) -> str:
    created = request(
        "POST",
        _SHEETS,
        json_body={"properties": {"title": title}},
    )
    spreadsheet_id = str(created.get("spreadsheetId") or "")
    if not spreadsheet_id:
        raise RuntimeError("spreadsheet create returned no id")
    request(
        "PATCH",
        f"{_DRIVE}/{spreadsheet_id}",
        params={"addParents": folder_id, "removeParents": "root", "supportsAllDrives": "true"},
    )
    return spreadsheet_id


def export_new_leads(
    rows: list[dict[str, str]],
    *,
    week_label: str,
    request: Request | None = None,
) -> dict[str, Any]:
    """Write this run's leads. Skips quietly when Google is not configured."""
    settings = get_settings()
    raw = (settings.google_service_account_json or "").strip()
    sheet_id = (settings.new_business_outreach_sheet_id or "").strip()
    folder_id = (settings.new_business_outreach_drive_folder_id or "").strip()
    if not raw or not (sheet_id or folder_id):
        logger.info(
            "New Business Outreach sheet export skipped; "
            "GOOGLE_SERVICE_ACCOUNT_JSON or a sheet/folder id is unset"
        )
        return {"ok": True, "skipped": True, "reason": "unconfigured", "rows": 0}

    try:
        info = _load_account(raw)
        caller = request or _http_request(_access_token(info))
        tab = _tab_title(week_label)
        if sheet_id:
            _ensure_tab(caller, sheet_id, tab)
            _write_values(caller, sheet_id, tab, rows)
            target = sheet_id
            mode = "tab"
        else:
            target = _create_in_folder(caller, folder_id, f"New Business Outreach {tab}")
            first = caller(
                "GET",
                f"{_SHEETS}/{target}",
                params={"fields": "sheets.properties.title"},
            )
            sheets = first.get("sheets") or []
            title = "Leads"
            if sheets:
                title = str((sheets[0].get("properties") or {}).get("title") or title)
            _write_values(caller, target, title, rows)
            mode = "spreadsheet"
    except Exception as exc:  # noqa: BLE001 — a sheet failure must not fail the scrape
        reraise_if_fatal(exc)
        logger.warning(
            "New Business Outreach sheet export failed (%s)",
            type(exc).__name__,
        )
        return {"ok": False, "skipped": False, "reason": type(exc).__name__, "rows": 0}

    logger.info(
        "New Business Outreach sheet export %s rows=%s mode=%s",
        week_label,
        len(rows),
        mode,
    )
    return {"ok": True, "skipped": False, "rows": len(rows), "mode": mode, "target": target}
