"""Weekly New Business Outreach window in Europe/Dublin, including DST.

One beat, default Sunday 00:00 Europe/Dublin (Saturday night into Sunday).
The weekday is configurable. The run must stop by 06:15 Europe/Dublin so the
07:00 and 19:00 zone scrapes keep every scrape worker and a cool Overpass.

Catch-up is only inside that window. A beat that was down at midnight still
starts at 02:00. It does not start at 07:00, and it does not start on Monday.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from celery.schedules import BaseSchedule, schedstate

from app.core.weekdays import WEEKDAY_NAMES, weekday_index, weekday_name
from app.scrapers.zones import zone_family

DUBLIN = ZoneInfo("Europe/Dublin")

# Midnight. The 07:00 zone scrapes are the next thing on the scrape queue.
OUTREACH_START_HOUR = 0
OUTREACH_START_MINUTE = 0
# Leave the workers and Overpass alone before the 07:00 cycle.
YIELD_HOUR = 6
YIELD_MINUTE = 15
# A message published at midnight must not still be runnable at 07:00.
OUTREACH_TASK_EXPIRES_SECONDS = (YIELD_HOUR * 60 + YIELD_MINUTE) * 60

# zones.py families. western_europe plus eastern_europe is the EU set:
# british_isles, iberia, france_benelux, dach_nordics, italy_adriatic,
# eastern_europe.
EU_ZONE_FAMILIES = frozenset({"western_europe", "eastern_europe"})
NA_ZONE_FAMILIES = frozenset({"north_america"})
EU_ZONE_ORDER: tuple[str, ...] = (
    "british_isles",
    "iberia",
    "france_benelux",
    "dach_nordics",
    "italy_adriatic",
    "eastern_europe",
)


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _dublin_wall(day: datetime, hour: int, minute: int) -> datetime:
    """``day``'s calendar date at hour:minute in Europe/Dublin (DST-aware)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=DUBLIN)


def lead_region(zone_id: str | None) -> str:
    """``EU``, ``NA``, or ``Other`` from the zone family in zones.py."""
    family = zone_family((zone_id or "").strip().lower())
    if family in EU_ZONE_FAMILIES:
        return "EU"
    if family in NA_ZONE_FAMILIES:
        return "NA"
    return "Other"


def is_eu_zone(zone_id: str | None) -> bool:
    return lead_region(zone_id) == "EU"


def last_weekly_slot(
    moment: datetime,
    *,
    weekday: int,
    hour: int,
    minute: int,
) -> datetime:
    """Most recent configured weekday at hour:minute Europe/Dublin, at or before ``moment``."""
    local = _as_utc(moment).astimezone(DUBLIN)
    days_back = (local.weekday() - weekday) % 7
    day = local.date() - timedelta(days=days_back)
    candidate = _dublin_wall(datetime.combine(day, datetime.min.time()), hour, minute)
    if candidate > local:
        day = day - timedelta(days=7)
        candidate = _dublin_wall(datetime.combine(day, datetime.min.time()), hour, minute)
    return candidate


def next_weekly_slot(
    moment: datetime,
    *,
    weekday: int,
    hour: int,
    minute: int,
) -> datetime:
    """First configured weekday at hour:minute Europe/Dublin strictly after ``moment``."""
    slot = last_weekly_slot(moment, weekday=weekday, hour=hour, minute=minute)
    nxt = slot.astimezone(DUBLIN) + timedelta(days=7)
    if nxt <= _as_utc(moment).astimezone(DUBLIN):
        nxt = nxt + timedelta(days=7)
    return nxt


def yield_deadline(slot: datetime, *, hour: int = YIELD_HOUR, minute: int = YIELD_MINUTE) -> datetime:
    """06:15 Europe/Dublin on the same calendar day as the midnight slot."""
    local = slot.astimezone(DUBLIN)
    return _dublin_wall(datetime.combine(local.date(), datetime.min.time()), hour, minute)


def inside_outreach_window(
    moment: datetime,
    *,
    weekday: int,
    hour: int = OUTREACH_START_HOUR,
    minute: int = OUTREACH_START_MINUTE,
) -> bool:
    """True from the weekly start until the yield clock, exclusive of the deadline."""
    slot = last_weekly_slot(moment, weekday=weekday, hour=hour, minute=minute)
    deadline = yield_deadline(slot)
    current = _as_utc(moment)
    if deadline <= slot:
        return False
    return slot <= current < deadline


def should_yield(
    moment: datetime | None = None,
    *,
    weekday: int,
    hour: int = OUTREACH_START_HOUR,
    minute: int = OUTREACH_START_MINUTE,
) -> bool:
    """True when the run must stop so 07:00 zone scrapes keep priority."""
    return not inside_outreach_window(
        moment or datetime.now(timezone.utc),
        weekday=weekday,
        hour=hour,
        minute=minute,
    )


class EuropeDublinWeekly(BaseSchedule):
    """Fire once a week at a Europe/Dublin wall time, and only until the yield clock."""

    def __init__(
        self,
        hour: int = OUTREACH_START_HOUR,
        minute: int = OUTREACH_START_MINUTE,
        weekday: int = 6,
        yield_hour: int = YIELD_HOUR,
        yield_minute: int = YIELD_MINUTE,
        nowfun: object | None = None,
        app: object | None = None,
    ) -> None:
        super().__init__(nowfun=nowfun, app=app)
        self.hour = int(hour)
        self.minute = int(minute)
        self.weekday = int(weekday)
        self.yield_hour = int(yield_hour)
        self.yield_minute = int(yield_minute)

    def __repr__(self) -> str:
        name = WEEKDAY_NAMES[self.weekday].capitalize()
        return (
            f"<EuropeDublinWeekly {name} {self.hour:02d}:{self.minute:02d} "
            f"Europe/Dublin, yields {self.yield_hour:02d}:{self.yield_minute:02d}>"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EuropeDublinWeekly):
            return NotImplemented
        return (
            self.hour,
            self.minute,
            self.weekday,
            self.yield_hour,
            self.yield_minute,
        ) == (
            other.hour,
            other.minute,
            other.weekday,
            other.yield_hour,
            other.yield_minute,
        )

    def remaining_estimate(self, last_run_at: datetime | None) -> timedelta:
        due, nxt = self.is_due(last_run_at)
        if due:
            return timedelta(0)
        return timedelta(seconds=nxt)

    def is_due(self, last_run_at: datetime | None) -> schedstate:
        now = _as_utc(self.now())
        last = (
            _as_utc(last_run_at)
            if last_run_at is not None
            else datetime(1970, 1, 1, tzinfo=timezone.utc)
        )
        slot = last_weekly_slot(
            now, weekday=self.weekday, hour=self.hour, minute=self.minute
        )
        deadline = yield_deadline(slot, hour=self.yield_hour, minute=self.yield_minute)
        following = next_weekly_slot(
            now, weekday=self.weekday, hour=self.hour, minute=self.minute
        )
        wait = max((following - now).total_seconds(), 1.0)
        window_open = deadline > slot and slot <= now < deadline
        if window_open and last < slot:
            return schedstate(True, wait)
        return schedstate(False, wait)
