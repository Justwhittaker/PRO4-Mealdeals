"""Celery application with stub periodic tasks."""

from __future__ import annotations

import logging
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

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
        "scrape-global-retail-every-6h": {
            "task": "app.workers.tasks.scrape_global_retail",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        # Weekly specials — every Friday 09:00 UTC
        "send-weekly-specials-friday": {
            "task": "app.workers.tasks.send_weekly_specials",
            "schedule": crontab(minute=0, hour=9, day_of_week="fri"),
        },
    },
)
