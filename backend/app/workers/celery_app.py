"""Celery application with stub periodic tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    after_setup_logger,
    after_setup_task_logger,
    before_task_publish,
    worker_process_init,
)

from app.core.config import get_settings
from app.core.log_quiet import quiet_http_client_logs
from app.scrapers.zones import (
    DIGEST_HOURS,
    MAINTENANCE_QUEUE,
    REDIS_VISIBILITY_TIMEOUT_SECONDS,
    SCRAPE_QUEUE,
    SCRAPE_TIMEZONE,
    SCRAPE_ZONES,
    ZONE_BEAT_SLOTS,
    ZONE_CYCLE_BASE_HOURS,
    ZONE_ORDER,
    ZONE_TASK_EXPIRES_SECONDS,
    validate_zone_coverage,
)
from app.services.scrape_cycle_stats import (
    cycle_id_for_start,
    cycle_start_for_time,
    remember_cycle_zone_set,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class DublinCrontab(crontab):
    """Crontab whose hour and minute are Europe/Dublin wall-clock, DST included.

    Beat stores ``last_run_at`` in the app timezone (UTC). Comparing those
    clock fields directly would schedule 07:00 UTC in winter. Convert the
    last run into Dublin before the hour math, and read "now" in Dublin too.
    """

    def now(self) -> datetime:
        return datetime.now(SCRAPE_TIMEZONE)

    def remaining_delta(  # type: ignore[override]
        self,
        last_run_at: datetime,
        tz: object = None,
        ffwd: object = None,
    ):
        if last_run_at.tzinfo is None:
            last_run_at = last_run_at.replace(tzinfo=timezone.utc)
        dublin_last = last_run_at.astimezone(SCRAPE_TIMEZONE)
        if ffwd is None:
            return super().remaining_delta(dublin_last, tz=tz)
        return super().remaining_delta(dublin_last, tz=tz, ffwd=ffwd)

celery_app = Celery(
    "mealdeals",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

# Zone scrapes and short maintenance tasks must not share worker slots.
# A 2–4h zone on the only concurrency slots delays the digest and hourly
# expiry/currency jobs until a slot frees. The digest itself is 18:00 / 06:00 Dublin.
_TASK_ROUTES = {
    "app.workers.tasks.scrape_zone_retail": {"queue": SCRAPE_QUEUE},
    "app.workers.tasks.scrape_global_retail": {"queue": SCRAPE_QUEUE},
    "app.workers.tasks.scrape_area": {"queue": SCRAPE_QUEUE},
    "app.workers.tasks.retry_failed_scrape_city": {"queue": SCRAPE_QUEUE},
    "app.workers.tasks.send_scrape_cycle_digest": {"queue": MAINTENANCE_QUEUE},
    "app.workers.tasks.expire_past_due_deals": {"queue": MAINTENANCE_QUEUE},
    "app.workers.tasks.update_currency_rates": {"queue": MAINTENANCE_QUEUE},
    "app.workers.tasks.send_weekly_specials": {"queue": MAINTENANCE_QUEUE},
    "app.workers.tasks.send_merchant_outreach": {"queue": MAINTENANCE_QUEUE},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # One reserved message per child. Prefetching the next multi-hour zone
    # while two are already running is how Redis' visibility timer used to
    # redeliver work that had not been acked yet.
    worker_prefetch_multiplier=1,
    # Longer than ZONE_TASK_TIME_LIMIT_SECONDS so a live zone is not
    # redelivered at the Redis broker's 1h default.
    broker_transport_options={
        "visibility_timeout": REDIS_VISIBILITY_TIMEOUT_SECONDS,
    },
    # A broker blip must not cancel a zone that is still running.
    worker_cancel_long_running_tasks_on_connection_loss=False,
    task_routes=_TASK_ROUTES,
    beat_schedule={
        "expire-past-due-deals-hourly": {
            "task": "app.workers.tasks.expire_past_due_deals",
            "schedule": crontab(minute=30),
            "options": {"queue": MAINTENANCE_QUEUE},
        },
        "update-currency-rates-hourly": {
            "task": "app.workers.tasks.update_currency_rates",
            "schedule": crontab(minute=15),
            "options": {"queue": MAINTENANCE_QUEUE},
        },
        # One hour before the next Dublin cycle. Covers the cycle ~11h earlier.
        # Sent on the clock even when zones or city retries are still running.
        "scrape-cycle-digest": {
            "task": "app.workers.tasks.send_scrape_cycle_digest",
            "schedule": DublinCrontab(minute=0, hour=",".join(str(hour) for hour in DIGEST_HOURS)),
            "options": {"queue": MAINTENANCE_QUEUE},
        },
    },
)

quiet_http_client_logs()


@after_setup_logger.connect
@after_setup_task_logger.connect
@worker_process_init.connect
def _quiet_http_client_logs(**_kwargs: object) -> None:
    # Celery configures logging after import and again in each prefork child.
    quiet_http_client_logs()


@before_task_publish.connect
def _stamp_scrape_cycle_id(
    sender: str | None = None,
    headers: dict | None = None,
    **_kwargs: object,
) -> None:
    """Attribute a zone result to the cycle that queued it, not the one it finished in."""
    if sender != "app.workers.tasks.scrape_zone_retail" or headers is None:
        return
    if not headers.get("scrape_cycle_id"):
        headers["scrape_cycle_id"] = cycle_id_for_start(cycle_start_for_time())
    # First publish in the cycle wins, so a mid-cycle rename keeps the set
    # these messages were actually scheduled with.
    remember_cycle_zone_set(str(headers["scrape_cycle_id"]), list(ZONE_ORDER))

if settings.celery_weekly_email_enabled:
    celery_app.conf.beat_schedule["send-weekly-specials-friday"] = {
        "task": "app.workers.tasks.send_weekly_specials",
        "schedule": crontab(minute=0, hour=9, day_of_week="fri"),
        "options": {"queue": MAINTENANCE_QUEUE},
    }
else:
    logger.info(
        "Celery weekly email beat disabled (CELERY_WEEKLY_EMAIL_ENABLED=false)"
    )

# Zone scrapes twice daily, staggered (see ZONE_BEAT_STAGGER_MINUTES).
# Smaller zones first, then the large-family splits (see ZONE_ORDER).
# Cycle blocks start 07:00 / 19:00 Europe/Dublin.
try:
    validate_zone_coverage()
except RuntimeError as exc:
    logger.warning("Scrape zone coverage incomplete: %s", exc)

for zone_id in ZONE_ORDER:
    minute, hour_offset = ZONE_BEAT_SLOTS[zone_id]
    label = SCRAPE_ZONES[zone_id]["label"]
    celery_app.conf.beat_schedule[f"scrape-zone-{zone_id}"] = {
        "task": "app.workers.tasks.scrape_zone_retail",
        "schedule": DublinCrontab(
            minute=minute,
            hour=[h + hour_offset for h in ZONE_CYCLE_BASE_HOURS],
        ),
        "kwargs": {"zone_id": zone_id},
        "options": {
            "expires": ZONE_TASK_EXPIRES_SECONDS,
            "queue": SCRAPE_QUEUE,
        },
    }
    logger.info(
        "Registered beat scrape zone %s (%s) at +%sh%02sm each 12h cycle (%s Europe/Dublin)",
        zone_id,
        label,
        hour_offset,
        minute,
        "/".join(f"{h:02d}:00" for h in ZONE_CYCLE_BASE_HOURS),
    )
