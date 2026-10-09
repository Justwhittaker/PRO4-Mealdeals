"""Sunday Fishy Finger Sub schedule in Europe/Dublin, including DST.

Deal scrapes stay on 06:00 and 18:00 UTC (07:00 and 19:00 Irish Summer Time).
This schedule does not use those cycle hours or the deal-cycle Redis keys.

Each zone keeps the same 10-minute stagger as ``ZONE_BEAT_SLOTS``, counted
from Sunday 08:00 Europe/Dublin. The first zone is 08:00. The digest is a
separate Sunday beat at 21:00 Europe/Dublin, after the staggered zones have
had the afternoon (the morning deal cycle also uses the scrape workers).

Catch-up is limited to ``FISHY_CATCHUP_HOURS`` after the slot. A beat that
was down all of Sunday does not start the scrape on Monday afternoon.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from celery.schedules import BaseSchedule, schedstate

from app.scrapers.zones import ZONE_BEAT_STAGGER_MINUTES, ZONE_ORDER

DUBLIN = ZoneInfo("Europe/Dublin")

# Sunday in datetime.weekday() (Monday is 0).
FISHY_WEEKDAY = 6
FISHY_START_HOUR = 8
FISHY_START_MINUTE = 0
FISHY_DIGEST_HOUR = 21
FISHY_DIGEST_MINUTE = 0
# Aligned with the queued task expiry. After this, wait for next Sunday.
FISHY_CATCHUP_HOURS = 18
FISHY_TASK_EXPIRES_SECONDS = FISHY_CATCHUP_HOURS * 60 * 60


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _dublin_wall(day: datetime, hour: int, minute: int) -> datetime:
    """Sunday-or-any date at hour:minute in Europe/Dublin (DST-aware)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=DUBLIN)


def next_dublin_sunday_after(
    moment: datetime,
    *,
    hour: int,
    minute: int,
) -> datetime:
    """First Sunday at ``hour:minute`` Europe/Dublin strictly after ``moment``."""
    local = _as_utc(moment).astimezone(DUBLIN)
    days_ahead = (FISHY_WEEKDAY - local.weekday()) % 7
    day = local.date() + timedelta(days=days_ahead)
    candidate = _dublin_wall(datetime.combine(day, datetime.min.time()), hour, minute)
    if candidate <= local:
        day = day + timedelta(days=7)
        candidate = _dublin_wall(datetime.combine(day, datetime.min.time()), hour, minute)
    return candidate


def last_dublin_sunday_at_or_before(
    moment: datetime,
    *,
    hour: int,
    minute: int,
) -> datetime:
    """Most recent Sunday at ``hour:minute`` Europe/Dublin at or before ``moment``."""
    nxt = next_dublin_sunday_after(moment, hour=hour, minute=minute)
    previous_day = nxt.astimezone(DUBLIN).date() - timedelta(days=7)
    return _dublin_wall(datetime.combine(previous_day, datetime.min.time()), hour, minute)


def fishy_zone_clock(zone_id: str) -> tuple[int, int]:
    """Local Dublin hour and minute for one zone, staggered like the deal beats."""
    index = ZONE_ORDER.index(zone_id)
    total = (FISHY_START_HOUR * 60 + FISHY_START_MINUTE) + (
        index * ZONE_BEAT_STAGGER_MINUTES
    )
    hour, minute = divmod(total, 60)
    return hour, minute


def fishy_week_start(now: datetime | None = None) -> datetime:
    """This run's window start: Sunday 08:00 Europe/Dublin, as UTC.

    Before 08:00 Dublin on Sunday, the window is the previous Sunday.
    """
    current = _as_utc(now or datetime.now(timezone.utc))
    start = last_dublin_sunday_at_or_before(
        current,
        hour=FISHY_START_HOUR,
        minute=FISHY_START_MINUTE,
    )
    return start.astimezone(timezone.utc)


class EuropeDublinWeekly(BaseSchedule):
    """Fire once a week at a Europe/Dublin wall time. Sunday only."""

    def __init__(
        self,
        hour: int,
        minute: int,
        nowfun: object | None = None,
        app: object | None = None,
    ) -> None:
        super().__init__(nowfun=nowfun, app=app)
        self.hour = int(hour)
        self.minute = int(minute)

    def __repr__(self) -> str:
        return f"<EuropeDublinWeekly Sunday {self.hour:02d}:{self.minute:02d} Europe/Dublin>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EuropeDublinWeekly):
            return NotImplemented
        return (self.hour, self.minute) == (other.hour, other.minute)

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
        slot = last_dublin_sunday_at_or_before(now, hour=self.hour, minute=self.minute)
        following = next_dublin_sunday_after(now, hour=self.hour, minute=self.minute)
        wait = max((following - now).total_seconds(), 1.0)
        within_catchup = (now - slot) <= timedelta(hours=FISHY_CATCHUP_HOURS)
        if last < slot and within_catchup:
            return schedstate(True, wait)
        return schedstate(False, wait)
