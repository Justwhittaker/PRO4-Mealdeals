"""Celery application with stub periodic tasks."""

from __future__ import annotations

import logging
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings
from app.scrapers.zones import (
    SCRAPE_ZONES,
    ZONE_BEAT_SLOTS,
    ZONE_CYCLE_BASE_HOURS,
    ZONE_ORDER,
    ZONE_TASK_EXPIRES_SECONDS,
    validate_zone_coverage,
)

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "mealdeals",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "expire-past-due-deals-hourly": {
            "task": "app.workers.tasks.expire_past_due_deals",
            "schedule": crontab(minute=30),
        },
        "update-currency-rates-hourly": {
            "task": "app.workers.tasks.update_currency_rates",
            "schedule": crontab(minute=15),
        },
        # After each twice-daily scrape window (almost 12h after 06:00 / 18:00 start).
        "scrape-cycle-digest": {
            "task": "app.workers.tasks.send_scrape_cycle_digest",
            "schedule": crontab(minute=50, hour="5,17"),
        },
    },
)

if settings.celery_weekly_email_enabled:
    celery_app.conf.beat_schedule["send-weekly-specials-friday"] = {
        "task": "app.workers.tasks.send_weekly_specials",
        "schedule": crontab(minute=0, hour=9, day_of_week="fri"),
    }
else:
    logger.info(
        "Celery weekly email beat disabled (CELERY_WEEKLY_EMAIL_ENABLED=false)"
    )

# Eight continental zone scrapes twice daily, staggered 15 minutes apart.
# Cycle blocks: 06:00–07:45 and 18:00–19:45 UTC (small zones first).
try:
    validate_zone_coverage()
except RuntimeError as exc:
    logger.warning("Scrape zone coverage incomplete: %s", exc)

for zone_id in ZONE_ORDER:
    minute, hour_offset = ZONE_BEAT_SLOTS[zone_id]
    label = SCRAPE_ZONES[zone_id]["label"]
    celery_app.conf.beat_schedule[f"scrape-zone-{zone_id}"] = {
        "task": "app.workers.tasks.scrape_zone_retail",
        "schedule": crontab(
            minute=minute,
            hour=[h + hour_offset for h in ZONE_CYCLE_BASE_HOURS],
        ),
        "kwargs": {"zone_id": zone_id},
        "options": {"expires": ZONE_TASK_EXPIRES_SECONDS},
    }
    logger.info(
        "Registered beat scrape zone %s (%s) at +%sh%02sm each 12h cycle (%s UTC)",
        zone_id,
        label,
        hour_offset,
        minute,
        "/".join(f"{h:02d}:00" for h in ZONE_CYCLE_BASE_HOURS),
    )
