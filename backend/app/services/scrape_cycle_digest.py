"""Build and send the twice-daily scrape cycle ntfy digest."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.scrapers.categories import CATEGORY_ID_TO_LABEL, CATEGORY_ORDER
from app.scrapers.zones import (
    LARGE_ZONE_FAMILIES,
    ZONE_FAMILY_LABELS,
    ZONE_ORDER,
    ZONE_TASK_TIME_LIMIT_SECONDS,
    zone_family,
)
from app.services.ntfy import send_ntfy
from app.services.scrape_cycle_stats import (
    cycle_id_for_start,
    digest_cycle_start,
    load_cycle_zone_results,
    load_cycle_zone_set,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# A live worker is hard-killed at ZONE_TASK_TIME_LIMIT_SECONDS and never
# writes a terminal status. Wait past that limit before calling a running
# row interrupted, so a zone still inside its budget is left alone.
_RUNNING_GRACE_SECONDS = 15 * 60
_DUBLIN = ZoneInfo("Europe/Dublin")


def _engine() -> Engine:
    return create_engine(get_settings().database_url_sync, pool_pre_ping=True)


def _pct(part: int | float, whole: int | float) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * float(part) / float(whole), 1)


def _is_running(row: dict[str, Any]) -> bool:
    return str(row.get("status") or "") == "running"


def _is_failed(row: dict[str, Any]) -> bool:
    """Crashed, timed out, or still running inside its time budget.

    Overdue and orphaned running rows are classified as interrupted first.
    A running marker used to be filled in from partial DB activity and
    reported as ok.
    """
    if _is_running(row):
        return True
    if row.get("ok") is False or row.get("error"):
        return True
    return False


def _parse_recorded_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _owning_worker_gone(row: dict[str, Any], alive_workers: set[str] | None) -> bool:
    """True when ping answered and this row's worker was not among the replies.

    ``None`` or an empty ping means liveness is unknown. That must not flag
    every running zone: the maintenance worker runs this digest at concurrency
    1 and may not answer its own ping while the task is in progress.
    """
    if not alive_workers:
        return False
    hostname = str(row.get("worker_hostname") or "").strip()
    if not hostname:
        return False
    return hostname not in alive_workers


def _is_interrupted(
    row: dict[str, Any],
    *,
    now: datetime | None,
    alive_workers: set[str] | None,
) -> bool:
    if not _is_running(row):
        return False
    if _owning_worker_gone(row, alive_workers):
        return True
    recorded = _parse_recorded_at(row.get("recorded_at"))
    if now is None or recorded is None:
        return False
    limit = ZONE_TASK_TIME_LIMIT_SECONDS + _RUNNING_GRACE_SECONDS
    return (now - recorded).total_seconds() > limit


def _alive_worker_hostnames() -> set[str] | None:
    """Hostnames that answered ping, or None when liveness is unknown."""
    try:
        replies = celery_app.control.ping(timeout=2.0)
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.warning(
            "Worker ping failed; digest will not use worker liveness: %s",
            exc,
        )
        return None
    if not isinstance(replies, list) or not replies:
        return None
    names: set[str] = set()
    for reply in replies:
        if isinstance(reply, dict):
            names.update(str(name) for name in reply)
    return names or None


def _zone_health(
    cycle_results: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
    alive_workers: set[str] | None = None,
    scheduled_zones: list[str] | None = None,
) -> dict[str, Any]:
    now_utc = None
    if now is not None:
        now_utc = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        now_utc = now_utc.astimezone(timezone.utc)

    current = list(ZONE_ORDER)
    current_set = set(current)
    foreign = sorted(zone for zone in cycle_results if zone not in current_set)
    scheduled = [
        str(zone).strip().lower()
        for zone in (scheduled_zones or [])
        if str(zone).strip()
    ]
    scheduled_differs = bool(scheduled) and set(scheduled) != current_set
    if scheduled_differs:
        extra = [zone for zone in foreign if zone not in set(scheduled)]
        scope = list(dict.fromkeys([*scheduled, *extra]))
        retired = [zone for zone in scheduled if zone not in current_set]
        note = "cycle used a different zone set than the one configured now"
        if retired:
            note += f" (scheduled only: {', '.join(retired)})"
    elif foreign:
        scope = [zone for zone in current if zone in cycle_results] + foreign
        note = (
            "recorded zones are not the current set "
            f"({', '.join(foreign)}); reporting recorded zones only"
        )
    else:
        scope = current
        note = None

    interrupted: list[str] = []
    failed: list[str] = []
    for zone_id in scope:
        row = cycle_results.get(zone_id)
        if not row:
            continue
        if _is_interrupted(row, now=now_utc, alive_workers=alive_workers):
            interrupted.append(zone_id)
        elif _is_failed(row):
            failed.append(zone_id)

    completed = [
        zone_id
        for zone_id in scope
        if zone_id in cycle_results and not _is_running(cycle_results[zone_id])
    ]
    ok_zones = [zone_id for zone_id in completed if zone_id not in failed]
    timed_out: list[str] = []
    for zone_id in scope:
        row = cycle_results.get(zone_id) or {}
        if str(row.get("status") or "") != "timed_out":
            continue
        done = row.get("areas", 0)
        total_areas = row.get("areas_total", "?")
        timed_out.append(
            f"{zone_id} {done}/{total_areas} cities, {row.get('ingested', 0)} ingested"
        )
    total = len(scope)
    city_errors = 0
    for row in cycle_results.values():
        failed_cities = row.get("cities_failed") or []
        if isinstance(failed_cities, list):
            city_errors += len(failed_cities)

    large_families: list[dict[str, Any]] = []
    if note is None:
        family_stats: dict[str, dict[str, Any]] = {}
        for zone_id in ZONE_ORDER:
            family = zone_family(zone_id)
            bucket = family_stats.setdefault(
                family,
                {"zones": [], "completed": 0, "ok": 0, "total": 0},
            )
            bucket["total"] += 1
            bucket["zones"].append(zone_id)
            if zone_id in cycle_results and not _is_running(cycle_results[zone_id]):
                bucket["completed"] += 1
                if zone_id not in failed:
                    bucket["ok"] += 1

        for family in LARGE_ZONE_FAMILIES:
            bucket = family_stats.get(family)
            if not bucket:
                continue
            large_families.append(
                {
                    "family": family,
                    "label": ZONE_FAMILY_LABELS.get(family, family),
                    "pct_completed": _pct(bucket["completed"], bucket["total"]),
                    "completed": bucket["completed"],
                    "total": bucket["total"],
                    "zones": bucket["zones"],
                }
            )

    return {
        "total_zones": total,
        "completed": len(completed),
        "ok": len(ok_zones),
        "failed": failed,
        "interrupted": interrupted,
        "timed_out": timed_out,
        "missing": [zone_id for zone_id in scope if zone_id not in cycle_results],
        "pct_completed": _pct(len(completed), total),
        "pct_ok": _pct(len(ok_zones), total),
        "large_families": large_families,
        "city_errors": city_errors,
        "zone_set_note": note,
    }


def _sum_cycle_metric(cycle_results: dict[str, dict[str, Any]], key: str) -> int:
    total = 0
    for row in cycle_results.values():
        try:
            total += int(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _query_window_counts(engine: Engine, since: datetime) -> dict[str, int]:
    with engine.connect() as conn:
        new_deals = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM deals
                    WHERE created_at >= :since
                      AND deleted_at IS NULL
                      AND scraped_raw_url IS NOT NULL
                    """
                ),
                {"since": since},
            ).scalar_one()
        )
        # Stale deactivation sets expires_at ≈ now and is_active=false.
        dropped = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM deals
                    WHERE scraped_raw_url IS NOT NULL
                      AND is_active IS FALSE
                      AND expires_at IS NOT NULL
                      AND expires_at >= :since
                    """
                ),
                {"since": since},
            ).scalar_one()
        )
        # Re-scrape sets updated_at on every existing contact, including ones
        # that already had an email. There is no column for when the email
        # was first filled in, so the honest window count is contacts created
        # in this cycle that have a non-empty email.
        new_email_rows = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM marketing_contacts
                    WHERE email IS NOT NULL
                      AND BTRIM(email) <> ''
                      AND created_at >= :since
                    """
                ),
                {"since": since},
            ).scalar_one()
        )
        active_scraped = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM deals
                    WHERE is_active IS TRUE
                      AND deleted_at IS NULL
                      AND scraped_raw_url IS NOT NULL
                    """
                )
            ).scalar_one()
        )
        # Same inventory count as GET /api/v1/scrapers/metrics active_deals,
        # which is the "N deals" figure in the public site header.
        active_site = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM deals
                    WHERE is_active IS TRUE
                    """
                )
            ).scalar_one()
        )
    return {
        "new_deals": new_deals,
        "dropped_deals": dropped,
        "net_new_emails": new_email_rows,
        "new_email_rows": new_email_rows,
        "active_scraped_deals": active_scraped,
        "active_site_deals": active_site,
    }


def _active_offers_on_site(api_active: int | None, db_active: int) -> int:
    """Header deal total. Metrics when the API answered, otherwise the DB count."""
    if api_active is None:
        return db_active
    return api_active


def _category_breakdown(engine: Engine) -> list[tuple[str, int, float]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COALESCE(venue_category, '') AS cat, COUNT(*) AS n
                FROM deals
                WHERE is_active IS TRUE
                  AND deleted_at IS NULL
                GROUP BY 1
                """
            )
        ).all()
    counts: dict[str, int] = {}
    total = 0
    for cat, n in rows:
        key = (cat or "").strip() or "uncategorized"
        label = CATEGORY_ID_TO_LABEL.get(key, key)
        counts[label] = counts.get(label, 0) + int(n)
        total += int(n)

    ordered: list[tuple[str, int, float]] = []
    seen: set[str] = set()
    for label in CATEGORY_ORDER:
        n = counts.get(label, 0)
        ordered.append((label, n, _pct(n, total)))
        seen.add(label)
    for label, n in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if label in seen:
            continue
        ordered.append((label, n, _pct(n, total)))
    return ordered


def _site_transfer_health(
    *,
    cycle_results: dict[str, dict[str, Any]],
    db_active: int,
) -> dict[str, Any]:
    revalidate_ok = _sum_cycle_metric(cycle_results, "revalidate_ok")
    revalidate_fail = _sum_cycle_metric(cycle_results, "revalidate_fail")
    revalidate_attempts = revalidate_ok + revalidate_fail
    revalidate_pct = _pct(revalidate_ok, revalidate_attempts) if revalidate_attempts else None

    settings = get_settings()
    api_base = (settings.public_api_base_url or "").rstrip("/")
    frontend = (settings.frontend_base_url or "").rstrip("/")
    api_active: int | None = None
    api_ok = False
    frontend_ok = False
    detail_parts: list[str] = []

    if api_base:
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(f"{api_base}/api/v1/scrapers/metrics")
            api_ok = resp.status_code == 200
            if api_ok:
                api_active = int(resp.json().get("active_deals") or 0)
            else:
                detail_parts.append(f"metrics HTTP {resp.status_code}")
        except Exception as exc:
            detail_parts.append(f"metrics error: {exc}")

    if frontend:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(frontend)
            frontend_ok = resp.status_code == 200
            if not frontend_ok:
                detail_parts.append(f"site HTTP {resp.status_code}")
        except Exception as exc:
            detail_parts.append(f"site error: {exc}")

    delta = None if api_active is None else abs(api_active - db_active)
    in_sync = delta is not None and delta <= max(25, int(db_active * 0.02))

    healthy = bool(api_ok and frontend_ok and (revalidate_fail == 0 or revalidate_pct is None or revalidate_pct >= 90))
    if api_active is not None and not in_sync:
        healthy = False
        detail_parts.append(f"active delta {delta} (db={db_active} api={api_active})")

    return {
        "healthy": healthy,
        "api_ok": api_ok,
        "frontend_ok": frontend_ok,
        "api_active_deals": api_active,
        "db_active_deals": db_active,
        "in_sync": in_sync,
        "revalidate_ok": revalidate_ok,
        "revalidate_fail": revalidate_fail,
        "revalidate_pct": revalidate_pct,
        "detail": "; ".join(detail_parts) if detail_parts else "ok",
    }


def _coerce_utc(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return _parse_recorded_at(value)


def _format_dublin_duration(
    started_at: datetime,
    finished_at: datetime,
    *,
    approximate: bool,
) -> str | None:
    start_local = started_at.astimezone(_DUBLIN).replace(second=0, microsecond=0)
    finish_local = finished_at.astimezone(_DUBLIN).replace(second=0, microsecond=0)
    minutes = int((finish_local - start_local).total_seconds() // 60)
    if minutes < 0:
        return None
    hours, mins = divmod(minutes, 60)
    start_clock = start_local.strftime("%H:%M")
    if approximate:
        start_clock = f"~{start_clock}"
    finish_clock = finish_local.strftime("%H:%M")
    return f"Duration: {hours}h {mins}m ({start_clock}–{finish_clock} Dublin)"


def _cycle_duration_line(
    cycle_results: dict[str, dict[str, Any]],
    *,
    since: datetime | str | None = None,
) -> str | None:
    """Earliest zone start through the latest finished zone, in Dublin time.

    Finish time comes from zones that have left the running state. A running
    row's recorded_at is the moment that marker was written. When no zone
    stored started_at, the scheduled cycle start (since) is the start and is
    prefixed with ~. With no finished zone, there is no duration line.
    """
    starts: list[datetime] = []
    finishes: list[datetime] = []
    for row in cycle_results.values():
        if not isinstance(row, dict):
            continue
        started = _parse_recorded_at(row.get("started_at"))
        if started is not None:
            starts.append(started)
        if _is_running(row):
            continue
        finished = _parse_recorded_at(row.get("recorded_at"))
        if finished is not None:
            finishes.append(finished)
    if not finishes:
        return None
    if starts:
        started_at = min(starts)
        approximate = False
    else:
        started_at = _coerce_utc(since)
        if started_at is None:
            return None
        approximate = True
    return _format_dublin_duration(
        started_at,
        max(finishes),
        approximate=approximate,
    )


def format_digest_body(report: dict[str, Any]) -> str:
    zones = report["zones"]
    site = report["site"]
    cats = report["categories"]

    zone_line = (
        f"Zones: {zones['pct_completed']:.0f}% completed "
        f"({zones['completed']}/{zones['total_zones']}), "
        f"{zones['pct_ok']:.0f}% ok"
    )
    if zones.get("zone_set_note"):
        zone_line += f"\nZone set: {zones['zone_set_note']}"
    if zones["missing"]:
        zone_line += f"\nMissing: {', '.join(zones['missing'])}"
    if zones["failed"]:
        zone_line += f"\nFailed: {', '.join(zones['failed'])}"
    if zones.get("interrupted"):
        zone_line += f"\nInterrupted: {', '.join(zones['interrupted'])}"
    if zones.get("timed_out"):
        zone_line += "\nTimed out: " + "; ".join(zones["timed_out"])
    if zones.get("city_errors"):
        zone_line += f"\nCity errors skipped: {zones['city_errors']}"
    for family in zones.get("large_families") or []:
        zone_line += (
            f"\nLarge · {family['label']}: "
            f"{family['pct_completed']:.0f}% "
            f"({family['completed']}/{family['total']})"
        )

    if site["revalidate_pct"] is None:
        rev = "no revalidate attempts recorded"
    else:
        rev = (
            f"revalidate {site['revalidate_pct']:.0f}% "
            f"({site['revalidate_ok']} ok / {site['revalidate_fail']} fail)"
        )
    site_line = (
        f"Site transfer: {'OK' if site['healthy'] else 'CHECK'} — {rev}"
        f"\nLive: api={'up' if site['api_ok'] else 'down'}, "
        f"web={'up' if site['frontend_ok'] else 'down'}"
    )
    if site["detail"] and site["detail"] != "ok":
        site_line += f"\n({site['detail']})"

    cat_lines = []
    for label, count, pct in cats:
        short = label.split(",")[0] if "," in label else label
        if len(short) > 28:
            short = short[:27] + "…"
        cat_lines.append(f"• {short}: {pct:.0f}% ({count})")

    raw_results = report.get("cycle_results")
    cycle_results = raw_results if isinstance(raw_results, dict) else {}
    duration_line = _cycle_duration_line(cycle_results, since=report.get("since"))
    lines = [f"Cycle {report['cycle_id']} (since {report['since_label']} UTC)"]
    if duration_line:
        lines.append(duration_line)
    lines.extend(
        [
            zone_line,
            site_line,
            f"Active offers on site: {report['active_offers']}",
            f"New deals: {report['new_deals']}",
            f"Dropped deals: {report['dropped_deals']}",
            f"New merchant emails (new contacts): {report['net_new_emails']}",
            "Category mix (active on site):",
            *cat_lines,
        ]
    )
    return "\n".join(lines)


def build_cycle_digest_report(now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    start = digest_cycle_start(current)
    cycle_id = cycle_id_for_start(start)
    cycle_results = load_cycle_zone_results(cycle_id)
    scheduled_zones = load_cycle_zone_set(cycle_id)

    engine = _engine()
    window = _query_window_counts(engine, start)
    categories = _category_breakdown(engine)

    # Do not invent ok=True from partial marketing_contacts touches. A zone
    # that scraped a few cities and then crashed must stay failed or missing.
    zones = _zone_health(
        cycle_results,
        now=current,
        alive_workers=_alive_worker_hostnames(),
        scheduled_zones=scheduled_zones,
    )
    # Prefer Redis-accumulated drops when present; else DB proxy.
    redis_dropped = _sum_cycle_metric(cycle_results, "stale_deactivated")
    dropped = redis_dropped if redis_dropped > 0 else window["dropped_deals"]

    site = _site_transfer_health(
        cycle_results=cycle_results,
        db_active=window["active_scraped_deals"],
    )
    api_active = site.get("api_active_deals")
    active_offers = _active_offers_on_site(
        api_active if isinstance(api_active, int) else None,
        window["active_site_deals"],
    )

    return {
        "cycle_id": cycle_id,
        "since": start.isoformat(),
        "since_label": start.strftime("%Y-%m-%d %H:%M"),
        "zones": zones,
        "site": site,
        "new_deals": window["new_deals"],
        "dropped_deals": dropped,
        "net_new_emails": window["net_new_emails"],
        "active_offers": active_offers,
        "categories": categories,
        "cycle_results": cycle_results,
    }


def run_scrape_cycle_digest(now: datetime | None = None) -> dict[str, Any]:
    """Build the cycle report and push it to ntfy."""
    report = build_cycle_digest_report(now=now)
    body = format_digest_body(report)
    zones = report["zones"]
    site = report["site"]
    priority = "default"
    tags = "newspaper"
    if zones["pct_completed"] < 100 or not site["healthy"]:
        priority = "high"
        tags = "warning,newspaper"
    if zones["pct_completed"] < 50 or (not site["api_ok"] and not site["frontend_ok"]):
        priority = "urgent"
        tags = "rotating_light,newspaper"

    notify = send_ntfy(
        "MealDeals scrape cycle digest",
        body,
        priority=priority,
        tags=tags,
    )
    logger.info(
        "Scrape cycle digest sent cycle=%s zones=%s%% new_deals=%s emails=%s ntfy=%s",
        report["cycle_id"],
        zones["pct_completed"],
        report["new_deals"],
        report["net_new_emails"],
        notify,
    )
    return {"report": report, "body": body, "ntfy": notify}
