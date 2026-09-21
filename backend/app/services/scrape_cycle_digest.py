"""Build and send the twice-daily scrape cycle ntfy digest."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.scrapers.categories import CATEGORY_ID_TO_LABEL, CATEGORY_ORDER
from app.scrapers.zones import ZONE_ORDER, zone_for_country
from app.services.ntfy import send_ntfy
from app.services.scrape_cycle_stats import (
    cycle_id_for_start,
    digest_cycle_start,
    load_cycle_zone_results,
)

logger = logging.getLogger(__name__)


def _engine() -> Engine:
    return create_engine(get_settings().database_url_sync, pool_pre_ping=True)


def _pct(part: int | float, whole: int | float) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * float(part) / float(whole), 1)


def _zone_health(cycle_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    completed = [z for z in ZONE_ORDER if z in cycle_results]
    failed = [
        z
        for z, row in cycle_results.items()
        if row.get("ok") is False or row.get("error")
    ]
    ok_zones = [z for z in completed if z not in failed]
    total = len(ZONE_ORDER)
    return {
        "total_zones": total,
        "completed": len(completed),
        "ok": len(ok_zones),
        "failed": failed,
        "missing": [z for z in ZONE_ORDER if z not in cycle_results],
        "pct_completed": _pct(len(completed), total),
        "pct_ok": _pct(len(ok_zones), total),
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
        gained_email_rows = int(
            conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM marketing_contacts
                    WHERE email IS NOT NULL
                      AND BTRIM(email) <> ''
                      AND created_at < :since
                      AND updated_at >= :since
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
    return {
        "new_deals": new_deals,
        "dropped_deals": dropped,
        "net_new_emails": new_email_rows + gained_email_rows,
        "new_email_rows": new_email_rows,
        "gained_email_rows": gained_email_rows,
        "active_scraped_deals": active_scraped,
    }


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


def _countries_touched(engine: Engine, since: datetime) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT UPPER(country_code) FROM marketing_contacts
                WHERE last_scraped_at >= :since
                  AND country_code IS NOT NULL
                """
            ),
            {"since": since},
        ).all()
    return {str(r[0]).upper() for r in rows if r[0]}


def _infer_zones_from_db(since: datetime, engine: Engine) -> set[str]:
    zones: set[str] = set()
    for code in _countries_touched(engine, since):
        try:
            zones.add(zone_for_country(code))
        except KeyError:
            continue
    return zones


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


def format_digest_body(report: dict[str, Any]) -> str:
    zones = report["zones"]
    site = report["site"]
    cats = report["categories"]

    zone_line = (
        f"Zones: {zones['pct_completed']:.0f}% completed "
        f"({zones['completed']}/{zones['total_zones']}), "
        f"{zones['pct_ok']:.0f}% ok"
    )
    if zones["missing"]:
        zone_line += f"\nMissing: {', '.join(zones['missing'])}"
    if zones["failed"]:
        zone_line += f"\nFailed: {', '.join(zones['failed'])}"

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

    return "\n".join(
        [
            f"Cycle {report['cycle_id']} (since {report['since_label']} UTC)",
            zone_line,
            site_line,
            f"New deals: {report['new_deals']}",
            f"Dropped deals: {report['dropped_deals']}",
            f"Net new merchant emails: {report['net_new_emails']}",
            "Category mix (active on site):",
            *cat_lines,
        ]
    )


def build_cycle_digest_report(now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    start = digest_cycle_start(current)
    cycle_id = cycle_id_for_start(start)
    cycle_results = load_cycle_zone_results(cycle_id)

    engine = _engine()
    window = _query_window_counts(engine, start)
    categories = _category_breakdown(engine)

    # If Redis missed some zone writes, still credit zones with DB scrape touches.
    inferred = _infer_zones_from_db(start, engine)
    for zone in inferred:
        cycle_results.setdefault(
            zone,
            {
                "zone": zone,
                "ok": True,
                "inferred_from_db": True,
                "revalidate_ok": 0,
                "revalidate_fail": 0,
                "stale_deactivated": 0,
            },
        )

    zones = _zone_health(cycle_results)
    # Prefer Redis-accumulated drops when present; else DB proxy.
    redis_dropped = _sum_cycle_metric(cycle_results, "stale_deactivated")
    dropped = redis_dropped if redis_dropped > 0 else window["dropped_deals"]

    site = _site_transfer_health(
        cycle_results=cycle_results,
        db_active=window["active_scraped_deals"],
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
