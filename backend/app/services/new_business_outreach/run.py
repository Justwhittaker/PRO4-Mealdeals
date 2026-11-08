"""One weekly New Business Outreach pass.

Europe tiles first, then the rest of the planet. A checkpoint resumes the
following week. The run yields before 06:15 Europe/Dublin so the 07:00 zone
scrapes keep the workers. This module does not send email.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.scrapers.zones import SCRAPE_ZONES
from app.services.new_business_outreach.chains import brand_key, corporate_domain
from app.services.new_business_outreach.checkpoint import load_checkpoint, save_checkpoint
from app.services.new_business_outreach.constants import ON_SITE_REASONS
from app.services.new_business_outreach.db import open_session
from app.services.new_business_outreach.digest import format_outreach_digest, send_outreach_digest
from app.services.new_business_outreach.discover import clear_robots_cache
from app.services.new_business_outreach.email_quality import pick_best_email
from app.services.new_business_outreach.exclusion import (
    ExclusionIndex,
    exclusion_reason,
    load_blocked_emails,
    load_country_index,
)
from app.services.geo_names import normalize_city
from app.services.marketing_contacts import _clean_website as clean_site
from app.services.new_business_outreach.leads import (
    _city_key,
    _remember,
    insert_fishy_lead,
    lead_is_known,
    load_stored_chain_signals,
    select_fishy_leads,
)
from app.services.new_business_outreach.overpass_query import OverpassOutcome, query_overpass
from app.services.new_business_outreach.schedule import DUBLIN, should_yield, weekday_index
from app.services.new_business_outreach.search import candidates_from_elements, overpass_query
from app.services.new_business_outreach.sheets import export_new_leads
from app.services.new_business_outreach.specials import offer_found_in_html
from app.services.new_business_outreach.storage import LeadSizeGuard
from app.services.new_business_outreach.tiles import (
    MAX_TILE_RETRIES,
    TILES,
    OutreachTile,
    decode_pending,
    encode_pending,
    quadrants,
    record_tile_outcome,
    should_subdivide,
    slice_tiles,
    tile_by_id,
    tiles_for_zone,
    venues_for_fetch,
)
from app.services.new_business_outreach.types import AcceptedLead, VenueCandidate
from app.services.new_business_outreach.website_queue import (
    FetchBudget,
    attempt_website,
    enqueue_candidates,
    next_queue_rows,
    row_to_candidate,
)

logger = logging.getLogger(__name__)

INSERT_BATCH = 20
_SAMPLE_LIMIT = 5


@dataclass
class _Bucket:
    found: int = 0
    with_email: int = 0
    excluded: int = 0


@dataclass
class _RunStats:
    found: int = 0
    with_email: int = 0
    excluded_on_site: int = 0
    no_email: int = 0
    no_website: int = 0
    failed: list[str] = field(default_factory=list)
    reasons: dict[str, int] = field(default_factory=dict)
    by_zone: dict[str, _Bucket] = field(default_factory=dict)
    by_type: dict[str, _Bucket] = field(default_factory=dict)
    samples: list[dict[str, str]] = field(default_factory=list)
    sheet_rows: list[dict[str, str]] = field(default_factory=list)
    tiles_run: int = 0
    yielded: bool = False
    storage_stopped: bool = False
    website_deferred: int = 0
    website_fetches: int = 0

    def zone(self, key: str) -> _Bucket:
        bucket = self.by_zone.get(key)
        if bucket is None:
            bucket = _Bucket()
            self.by_zone[key] = bucket
        return bucket

    def kind(self, key: str) -> _Bucket:
        bucket = self.by_type.get(key)
        if bucket is None:
            bucket = _Bucket()
            self.by_type[key] = bucket
        return bucket

    def add_reason(self, reason: str, count: int = 1) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + count


def _run_coro(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _sheet_row(lead: AcceptedLead, found_at: datetime) -> dict[str, str]:
    return {
        "name": lead.business_name,
        "type": lead.venue_category,
        "country": lead.country_code,
        "region": lead.zone_id,
        "address": lead.address or "",
        "website": lead.website or "",
        "email": lead.email,
        "source": lead.lead_source or "osm",
        "found date": found_at.astimezone(DUBLIN).date().isoformat(),
    }


def _discover_tile(tile: OutreachTile, *, limit: int) -> tuple[list[VenueCandidate], OverpassOutcome]:
    outcome = _run_coro(
        query_overpass(
            overpass_query(tile, limit=limit),
            start=abs(hash(tile.tile_id)) % 4,
        )
    )
    if not outcome.ok:
        return [], outcome
    return candidates_from_elements(outcome.elements, tile), outcome


def _specials_key(name: str, city: str, website: str | None) -> tuple[str, str, str]:
    return (name.strip(), normalize_city(city), clean_site(website) or "")


def _prepare(
    candidates: list[VenueCandidate],
    *,
    extra_brand_cities: dict[str, set[tuple[str, str]]] | None = None,
    extra_domain_names: dict[str, set[str]] | None = None,
) -> tuple[list[tuple[AcceptedLead, bool | None]], dict[str, int]]:
    """Score leads from HTML already fetched. This does not request websites."""
    flagged: list[tuple[VenueCandidate, bool | None]] = []
    for candidate in candidates:
        flag = None
        if candidate.homepage_html:
            flag = offer_found_in_html(
                candidate.homepage_html,
                candidate.homepage_url or candidate.website or "",
            )
        flagged.append((replace(candidate, homepage_html=None), flag))
    accepted, filter_stats = select_fishy_leads(
        [item for item, _flag in flagged],
        extra_brand_cities=extra_brand_cities,
        extra_domain_names=extra_domain_names,
    )
    flags = {
        _specials_key(item.business_name, item.city, item.website): flag
        for item, flag in flagged
    }
    prepared = [
        (
            replace(
                lead,
                has_site_specials=flags.get(
                    _specials_key(lead.business_name, lead.city, lead.website)
                ),
            ),
            flags.get(_specials_key(lead.business_name, lead.city, lead.website)),
        )
        for lead in accepted
    ]
    return prepared, filter_stats


class _Indexes:
    def __init__(self) -> None:
        self.by_country: dict[str, ExclusionIndex] = {}
        self.unsubscribed: set[str] | None = None
        self.suppressed: set[str] | None = None
        self.brand_cities: dict[str, set[tuple[str, str]]] = {}
        self.domain_names: dict[str, set[str]] = {}

    def for_country(self, session: Any, country: str) -> ExclusionIndex:
        key = (country or "").strip().upper()
        cached = self.by_country.get(key)
        if cached is not None:
            return cached
        if self.unsubscribed is None or self.suppressed is None:
            self.unsubscribed, self.suppressed = load_blocked_emails(session)
        loaded = load_country_index(
            session,
            key,
            unsubscribed=self.unsubscribed,
            suppressed=self.suppressed,
        )
        self.by_country[key] = loaded
        return loaded

    def remember_lead(self, lead: AcceptedLead) -> None:
        """Keep a lead inserted earlier in this run visible to later tiles."""
        key = (lead.country_code or "").strip().upper()
        cached = self.by_country.get(key)
        if cached is None:
            return
        cached.add_contact(
            name=lead.business_name,
            country=lead.country_code,
            city=lead.city,
            website=lead.website,
            email=lead.email,
        )
        key_name = brand_key(lead.business_name)
        if key_name and lead.country_code and lead.city:
            self.brand_cities.setdefault(key_name, set()).add(
                _city_key(lead.country_code, lead.city)
            )
        domain = corporate_domain(lead.website)
        if domain and key_name:
            self.domain_names.setdefault(domain, set()).add(key_name)


def _note_kept(stats: _RunStats, lead: AcceptedLead, found_at: datetime, *, store_sheet: bool) -> None:
    stats.with_email += 1
    stats.zone(lead.zone_id).with_email += 1
    stats.kind(lead.venue_category).with_email += 1
    record = _sheet_row(lead, found_at)
    if store_sheet:
        stats.sheet_rows.append(record)
    if len(stats.samples) < _SAMPLE_LIMIT:
        stats.samples.append(record)


def _flush(
    session: Any,
    leads: list[AcceptedLead],
    known: set[tuple[str, str]],
    stats: _RunStats,
    found_at: datetime,
) -> int:
    inserted = 0
    for lead in leads:
        if lead_is_known(lead, known):
            stats.add_reason("existing_contact")
            stats.excluded_on_site += 1
            continue
        try:
            with session.begin_nested():
                row = insert_fishy_lead(session, lead)
            if row.last_outreach_sent_at is not None or row.about_blurb:
                raise RuntimeError("lead row must stay free of send state and page text")
            _remember(known, lead)
            inserted += 1
            _note_kept(stats, lead, found_at, store_sheet=True)
        except IntegrityError:
            stats.add_reason("existing_contact")
            stats.excluded_on_site += 1
    session.commit()
    return inserted


def _process_tile(
    tile: OutreachTile,
    stats: _RunStats,
    *,
    write: bool,
    indexes: _Indexes,
    guard: LeadSizeGuard | None,
    found_at: datetime,
) -> None:
    try:
        candidates, outcome = _discover_tile(
            tile,
            limit=int(get_settings().new_business_max_places_per_tile),
        )
    except Exception as exc:  # noqa: BLE001
        reraise_if_fatal(exc)
        logger.exception("New Business Outreach tile %s failed", tile.tile_id)
        stats.failed.append(tile.tile_id)
        return
    if not outcome.ok:
        logger.warning(
            "New Business Outreach skipped tile %s; Overpass mirrors failed: %s",
            tile.tile_id,
            outcome.error,
        )
        stats.failed.append(tile.tile_id)
        return

    stats.tiles_run += 1
    stats.found += len(candidates)
    for candidate in candidates:
        stats.zone(tile.lead_zone).found += 1
        stats.kind(candidate.venue_category).found += 1
        if not candidate.website:
            stats.no_website += 1
    prepared, filter_stats = _prepare(
        candidates,
        extra_brand_cities=indexes.brand_cities,
        extra_domain_names=indexes.domain_names,
    )
    for reason, count in filter_stats.items():
        if reason == "kept":
            continue
        stats.add_reason(reason, int(count))
        if reason == "email":
            stats.no_email += int(count)
    skip_own_ads = bool(get_settings().new_business_skip_own_ads)
    pending: list[AcceptedLead] = []
    for lead, flag in prepared:
        if skip_own_ads and flag is True:
            stats.add_reason("own_ads")
            continue
        pending.append(lead)

    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            if guard is not None:
                guard.refresh(session)
                if guard.stopped:
                    stats.storage_stopped = True
                    guard.warn_once()
                    return
            known: set[tuple[str, str]] = set()
            kept: list[AcceptedLead] = []
            for lead in pending:
                reason = exclusion_reason(lead, indexes.for_country(session, lead.country_code))
                if reason:
                    stats.add_reason(reason)
                    if reason in ON_SITE_REASONS:
                        stats.excluded_on_site += 1
                        stats.zone(lead.zone_id).excluded += 1
                        stats.kind(lead.venue_category).excluded += 1
                    continue
                kept.append(lead)
            if not write:
                for lead in kept:
                    _note_kept(stats, lead, found_at, store_sheet=False)
                return
            for offset in range(0, len(kept), INSERT_BATCH):
                if guard is not None and guard.stopped:
                    stats.storage_stopped = True
                    guard.warn_once()
                    break
                inserted = _flush(
                    session,
                    kept[offset : offset + INSERT_BATCH],
                    known,
                    stats,
                    found_at,
                )
                if guard is not None:
                    guard.note_inserts(inserted)
                    if guard.stopped:
                        stats.storage_stopped = True
                        guard.warn_once()
                        break
    finally:
        engine.dispose()


def _buckets(raw: dict[str, _Bucket]) -> dict[str, dict[str, int]]:
    return {
        key: {
            "found": bucket.found,
            "with_email": bucket.with_email,
            "excluded": bucket.excluded,
        }
        for key, bucket in raw.items()
    }


def _summary(
    stats: _RunStats,
    *,
    cycle: int,
    next_index: int,
    wrapped: bool,
    dry_run: bool,
    zone: str | None,
    sheet: dict[str, Any] | None,
    storage_mb: float,
    cap_mb: int,
    status: str,
) -> dict[str, Any]:
    settings = get_settings()
    return {
        "ok": status != "unknown_zone",
        "status": status,
        "dry_run": dry_run,
        "zone": zone,
        "outreach_sends": 0,
        "ntfy": None,
        "week_label": datetime.now(DUBLIN).date().isoformat(),
        "outreach_enabled": bool(settings.new_business_outreach_enabled),
        "tiles_total": len(TILES),
        "tiles_run": stats.tiles_run,
        "cycle": cycle,
        "next_tile_index": next_index,
        "wrapped": wrapped,
        "yielded": stats.yielded,
        "storage_stopped": stats.storage_stopped,
        "storage_mb": round(storage_mb, 1),
        "storage_cap_mb": cap_mb,
        "found": stats.found,
        "with_email": stats.with_email,
        "excluded_on_site": stats.excluded_on_site,
        "no_email": stats.no_email,
        "no_website": stats.no_website,
        "failed_tiles": list(stats.failed),
        "failed": len(stats.failed),
        "reasons": dict(stats.reasons),
        "by_zone": _buckets(stats.by_zone),
        "by_type": _buckets(stats.by_type),
        "samples": list(stats.samples),
        "sheet": sheet or {"skipped": True, "reason": "not_run"},
        "skip_own_ads": bool(settings.new_business_skip_own_ads),
        "website_deferred": stats.website_deferred,
        "website_fetches": stats.website_fetches,
    }


def _tiles_for(zone_id: str) -> list[OutreachTile]:
    key = zone_id.strip().lower()
    found = tiles_for_zone(key)
    if found:
        return found
    one = tile_by_id(key)
    if one is not None:
        return [one]
    return []


def _save_progress(
    next_index: int,
    cycle: int,
    pending: list[OutreachTile],
) -> None:
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            save_checkpoint(
                session,
                next_tile_index=next_index,
                cycle=cycle,
                pending_subtiles=encode_pending(pending),
            )
    finally:
        engine.dispose()


def _queue_needs(
    session: Any,
    needs: list[VenueCandidate],
    stats: _RunStats,
) -> None:
    queued = enqueue_candidates(session, needs)
    stats.website_deferred += queued


def _insert_ready(
    session: Any,
    candidates: list[VenueCandidate],
    stats: _RunStats,
    *,
    indexes: _Indexes,
    guard: LeadSizeGuard | None,
    found_at: datetime,
    write: bool,
) -> None:
    if not candidates:
        return
    prepared, filter_stats = _prepare(
        candidates,
        extra_brand_cities=indexes.brand_cities,
        extra_domain_names=indexes.domain_names,
    )
    for reason, count in filter_stats.items():
        if reason == "kept":
            continue
        stats.add_reason(reason, int(count))
        if reason == "email":
            stats.no_email += int(count)
    skip_own_ads = bool(get_settings().new_business_skip_own_ads)
    pending: list[AcceptedLead] = []
    for lead, flag in prepared:
        if skip_own_ads and flag is True:
            stats.add_reason("own_ads")
            continue
        pending.append(lead)
    if not write:
        for lead in pending:
            _note_kept(stats, lead, found_at, store_sheet=False)
        return
    if guard is not None:
        guard.refresh(session)
        if guard.stopped:
            stats.storage_stopped = True
            guard.warn_once()
            return
    known: set[tuple[str, str]] = set()
    kept: list[AcceptedLead] = []
    for lead in pending:
        reason = exclusion_reason(lead, indexes.for_country(session, lead.country_code))
        if reason:
            stats.add_reason(reason)
            if reason in ON_SITE_REASONS:
                stats.excluded_on_site += 1
                stats.zone(lead.zone_id).excluded += 1
                stats.kind(lead.venue_category).excluded += 1
            continue
        kept.append(lead)
    for offset in range(0, len(kept), INSERT_BATCH):
        if guard is not None and guard.stopped:
            stats.storage_stopped = True
            guard.warn_once()
            break
        batch = kept[offset : offset + INSERT_BATCH]
        inserted = _flush(
            session,
            batch,
            known,
            stats,
            found_at,
        )
        for lead in batch:
            indexes.remember_lead(lead)
        if guard is not None:
            guard.note_inserts(inserted)
            if guard.stopped:
                stats.storage_stopped = True
                guard.warn_once()
                break


def _fetch_allowed(stats: _RunStats, budget: FetchBudget, weekday: int) -> bool:
    if should_yield(datetime.now(timezone.utc), weekday=weekday):
        stats.yielded = True
        return False
    return budget.remaining > 0


def _drain_website_queue(
    stats: _RunStats,
    budget: FetchBudget,
    *,
    indexes: _Indexes,
    guard: LeadSizeGuard | None,
    found_at: datetime,
    weekday: int,
) -> None:
    """Spend this week's fetch budget on places carried over from earlier runs."""
    if budget.remaining <= 0 or stats.storage_stopped:
        return
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            rows = next_queue_rows(session, budget.remaining)
            for row in rows:
                if budget.remaining <= 0 or should_yield(datetime.now(timezone.utc), weekday=weekday):
                    stats.yielded = should_yield(datetime.now(timezone.utc), weekday=weekday)
                    break
                if guard is not None and guard.stopped:
                    break
                updated, status = attempt_website(
                    row_to_candidate(row),
                    budget,
                    allow=lambda: _fetch_allowed(stats, budget, weekday),
                )
                if status in {"skipped", "yielded"}:
                    break
                if status == "partial":
                    continue
                session.delete(row)
                session.commit()
                _insert_ready(
                    session,
                    [updated],
                    stats,
                    indexes=indexes,
                    guard=guard,
                    found_at=found_at,
                    write=True,
                )
    finally:
        engine.dispose()


def _persist_leaf(
    candidates: list[VenueCandidate],
    tile: OutreachTile,
    stats: _RunStats,
    budget: FetchBudget,
    *,
    indexes: _Indexes,
    guard: LeadSizeGuard | None,
    found_at: datetime,
    weekday: int,
) -> None:
    stats.tiles_run += 1
    stats.found += len(candidates)
    for candidate in candidates:
        stats.zone(tile.lead_zone).found += 1
        stats.kind(candidate.venue_category).found += 1
        if not candidate.website:
            stats.no_website += 1
    ready: list[VenueCandidate] = []
    needs: list[VenueCandidate] = []
    for candidate in candidates:
        if pick_best_email(candidate.emails).accepted or not candidate.website:
            ready.append(candidate)
        else:
            needs.append(candidate)
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            _insert_ready(
                session,
                ready,
                stats,
                indexes=indexes,
                guard=guard,
                found_at=found_at,
                write=True,
            )
            if stats.storage_stopped:
                _queue_needs(session, needs, stats)
                return
            start_count, _deferred = venues_for_fetch(len(needs), budget.remaining)
            still_waiting: list[VenueCandidate] = []
            for index, candidate in enumerate(needs):
                if stats.storage_stopped or index >= start_count:
                    still_waiting.extend(needs[index:])
                    break
                updated, status = attempt_website(
                    candidate,
                    budget,
                    allow=lambda: _fetch_allowed(stats, budget, weekday),
                )
                if status in {"skipped", "partial", "yielded"}:
                    still_waiting.extend(needs[index:])
                    break
                _insert_ready(
                    session,
                    [updated],
                    stats,
                    indexes=indexes,
                    guard=guard,
                    found_at=found_at,
                    write=True,
                )
            _queue_needs(session, still_waiting, stats)
    finally:
        engine.dispose()


def run_zone_dry(zone_id: str) -> dict[str, Any]:
    """Discover one zone. No writes, no email, no ntfy, no sheet."""
    key = zone_id.strip().lower()
    tiles = _tiles_for(key)
    cap_mb = int(get_settings().new_business_leads_max_mb)
    if not tiles:
        summary = _summary(
            _RunStats(),
            cycle=0,
            next_index=0,
            wrapped=False,
            dry_run=True,
            zone=key,
            sheet={"skipped": True, "reason": "dry_run"},
            storage_mb=0,
            cap_mb=cap_mb,
            status="unknown_zone" if key not in SCRAPE_ZONES else "empty_zone",
        )
        return summary
    clear_robots_cache()
    stats = _RunStats()
    found_at = datetime.now(timezone.utc)
    for tile in tiles:
        try:
            _process_tile(
                tile,
                stats,
                write=False,
                indexes=_Indexes(),
                guard=None,
                found_at=found_at,
            )
        except Exception as exc:  # noqa: BLE001 — dry run still prints what it could
            reraise_if_fatal(exc)
            logger.exception("Dry run tile %s failed", tile.tile_id)
            stats.failed.append(tile.tile_id)
    return _summary(
        stats,
        cycle=0,
        next_index=0,
        wrapped=False,
        dry_run=True,
        zone=key,
        sheet={"skipped": True, "reason": "dry_run"},
        storage_mb=0,
        cap_mb=cap_mb,
        status="completed",
    )


def run_new_business_outreach(now: datetime | None = None) -> dict[str, Any]:
    """Store the next batch of lean leads, then export and post the digest."""
    moment = now or datetime.now(timezone.utc)
    weekday = weekday_index(get_settings().new_business_outreach_weekday)
    cap_mb = int(get_settings().new_business_leads_max_mb)
    if should_yield(moment, weekday=weekday):
        logger.info("New Business Outreach skipped; outside the weekly window")
        return _summary(
            _RunStats(),
            cycle=0,
            next_index=0,
            wrapped=False,
            dry_run=False,
            zone=None,
            sheet=None,
            storage_mb=0,
            cap_mb=cap_mb,
            status="skipped_outside_window",
        )

    clear_robots_cache()
    stats = _RunStats()
    indexes = _Indexes()
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            start, cycle, pending_raw = load_checkpoint(session)
            indexes.brand_cities, indexes.domain_names = load_stored_chain_signals(session)
            guard = LeadSizeGuard(cap_mb * 1024 * 1024)
            guard.refresh(session)
            storage_bytes = guard.bytes
    finally:
        engine.dispose()

    settings = get_settings()
    budget = FetchBudget(int(settings.new_business_website_fetches_per_run))
    max_places = int(settings.new_business_max_places_per_tile)
    pending = decode_pending(pending_raw)
    found_at = datetime.now(timezone.utc)
    if guard.stopped:
        stats.storage_stopped = True
        guard.warn_once()
    else:
        _drain_website_queue(
            stats,
            budget,
            indexes=indexes,
            guard=guard,
            found_at=found_at,
            weekday=weekday,
        )

    next_index = start % len(TILES) if TILES else 0
    wrapped = False
    queries = 0
    query_limit = int(settings.new_business_tiles_per_run)
    while (
        queries < query_limit
        and not stats.yielded
        and not stats.storage_stopped
        and not wrapped
        and TILES
    ):
        if should_yield(datetime.now(timezone.utc), weekday=weekday):
            stats.yielded = True
            logger.info("New Business Outreach yielding before 07:00 Europe/Dublin")
            break
        from_static = False
        if pending:
            tile = pending.pop(0)
        else:
            tile = TILES[next_index]
            from_static = True
        queries += 1
        try:
            candidates, outcome = _discover_tile(tile, limit=max_places)
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
            logger.exception("New Business Outreach tile %s failed", tile.tile_id)
            outcome = None
            candidates = []
        raw_count = len(outcome.elements) if outcome is not None and outcome.ok else 0
        timed_out = bool(outcome is not None and outcome.timed_out)
        blocks_static = from_static or tile.tile_id == TILES[next_index].tile_id
        if outcome is not None and should_subdivide(
            tile,
            result_count=raw_count,
            timed_out=timed_out,
            max_places=max_places,
        ):
            children = quadrants(tile)
            pending = children + pending
            logger.info(
                "New Business Outreach split %s into %s sub-tiles",
                tile.tile_id,
                len(children),
            )
            progress = record_tile_outcome(
                index=next_index,
                pending=pending,
                cycle=cycle,
                tile=tile,
                blocks_static=blocks_static,
                success=True,
                tile_count=len(TILES),
            )
            next_index = progress.index
            cycle = progress.cycle
            pending = list(progress.pending)
            wrapped = progress.advanced and next_index == 0 and not pending
            _save_progress(next_index, cycle, pending)
            continue
        if outcome is None or not outcome.ok:
            progress = record_tile_outcome(
                index=next_index,
                pending=pending,
                cycle=cycle,
                tile=tile,
                blocks_static=blocks_static,
                success=False,
                tile_count=len(TILES),
            )
            next_index = progress.index
            cycle = progress.cycle
            pending = list(progress.pending)
            wrapped = progress.advanced and next_index == 0 and not pending
            if progress.dropped:
                stats.failed.append(tile.tile_id)
                logger.warning(
                    "New Business Outreach gave up on tile %s after %s tries: %s",
                    tile.tile_id,
                    tile.retries + 1,
                    None if outcome is None else outcome.error,
                )
            else:
                logger.warning(
                    "New Business Outreach will retry tile %s next run (%s/%s): %s",
                    tile.tile_id,
                    tile.retries + 1,
                    MAX_TILE_RETRIES,
                    None if outcome is None else outcome.error,
                )
            _save_progress(next_index, cycle, pending)
            if progress.retrying:
                break
            continue
        _persist_leaf(
            candidates,
            tile,
            stats,
            budget,
            indexes=indexes,
            guard=guard,
            found_at=found_at,
            weekday=weekday,
        )
        if stats.storage_stopped:
            pending.insert(0, tile)
            _save_progress(next_index, cycle, pending)
            break
        progress = record_tile_outcome(
            index=next_index,
            pending=pending,
            cycle=cycle,
            tile=tile,
            blocks_static=blocks_static,
            success=True,
            tile_count=len(TILES),
        )
        next_index = progress.index
        cycle = progress.cycle
        pending = list(progress.pending)
        wrapped = progress.advanced and next_index == 0 and not pending
        _save_progress(next_index, cycle, pending)

    stats.website_fetches = int(settings.new_business_website_fetches_per_run) - budget.remaining

    week_label = found_at.astimezone(DUBLIN).date().isoformat()
    sheet = export_new_leads(stats.sheet_rows, week_label=week_label)
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            guard.refresh(session)
            storage_bytes = guard.bytes
            if guard.stopped:
                stats.storage_stopped = True
                guard.warn_once()
    finally:
        engine.dispose()
    status = "completed"
    if stats.yielded:
        status = "yielded"
    if stats.storage_stopped:
        status = "storage_cap"
    summary = _summary(
        stats,
        cycle=cycle,
        next_index=next_index,
        wrapped=wrapped,
        dry_run=False,
        zone=None,
        sheet=sheet,
        storage_mb=storage_bytes / (1024 * 1024),
        cap_mb=cap_mb,
        status=status,
    )
    body = format_outreach_digest(summary)
    summary["digest_body"] = body
    summary["ntfy"] = send_outreach_digest(body)
    logger.info(
        "New Business Outreach tiles=%s found=%s email=%s excluded=%s failed=%s sends=0",
        stats.tiles_run,
        stats.found,
        stats.with_email,
        stats.excluded_on_site,
        len(stats.failed),
    )
    return summary
