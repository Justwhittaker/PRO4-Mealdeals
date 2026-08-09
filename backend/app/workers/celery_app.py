"""Celery application with stub periodic tasks."""

from __future__ import annotations

import logging
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings
from app.scrapers.zones import SCRAPE_ZONES, ZONE_BEAT_SLOTS, ZONE_ORDER, validate_zone_coverage

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
        "update-currency-rates-hourly": {
            "task": "app.workers.tasks.update_currency_rates",
            "schedule": crontab(minute=15),
        },
        # Weekly specials — every Friday 09:00 UTC
        "send-weekly-specials-friday": {
            "task": "app.workers.tasks.send_weekly_specials",
            "schedule": crontab(minute=0, hour=9, day_of_week="fri"),
        },
    },
)

# Eight continental zone scrapes every 6 hours, staggered 15 minutes apart.
# Cycle blocks: 00:00–01:45, 06:00–07:45, 12:00–13:45, 18:00–19:45 UTC.
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
            hour=[h + hour_offset for h in (0, 6, 12, 18)],
        ),
        "kwargs": {"zone_id": zone_id},
        "options": {"expires": 60 * 60 * 3},
    }
    logger.info(
        "Registered beat scrape zone %s (%s) at +%sh%02sm each 6h cycle",
        zone_id,
        label,
        hour_offset,
        minute,
    )
