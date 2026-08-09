"""Aggregate live product metrics from Postgres for staff dashboards."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.merchant import Merchant
from app.models.newsletter import NewsletterSubscriber
from app.schemas.dashboard_metrics import (
    AreaCount,
    DashboardMetricsRead,
    DashboardMetricsSummary,
    FeaturedAdArea,
    MerchantSubArea,
)


def _city_label(raw: str | None) -> str:
    value = (raw or "").strip()
    return value if value else "(unknown)"


def _country_label(raw: str | None) -> str:
    value = (raw or "").strip()
    return value if value else "(unknown)"


async def build_dashboard_metrics(session: AsyncSession) -> DashboardMetricsRead:
    """Country/city breakdowns for newsletter, merchants, featured ads, clicks."""

    click_rows = (
        await session.execute(
            text(
                """
                SELECT
                  COALESCE(l.country_code, '(unknown)') AS country,
                  COALESCE(NULLIF(TRIM(l.city), ''), '(unknown)') AS city,
                  COUNT(*)::int AS n
                FROM click_events c
                JOIN deals d ON d.id = c.deal_id
                JOIN merchants m ON m.id = d.merchant_id
                JOIN locations l ON l.id = m.location_id
                GROUP BY 1, 2
                ORDER BY n DESC
                """
            )
        )
    ).all()

    newsletter_rows = (
        await session.execute(
            select(
                NewsletterSubscriber.country_code,
                NewsletterSubscriber.city,
                NewsletterSubscriber.location,
                func.count().label("n"),
            )
            .where(NewsletterSubscriber.is_subscribed.is_(True))
            .group_by(
                NewsletterSubscriber.country_code,
                NewsletterSubscriber.city,
                NewsletterSubscriber.location,
            )
            .order_by(func.count().desc())
        )
    ).all()

    merchant_area_rows = (
        await session.execute(
            select(
                Location.country_code,
                Location.city,
                Merchant.subscription_phase,
                Merchant.tier_level,
                Merchant.is_subscriber,
            )
            .join(Location, Location.id == Merchant.location_id)
            .where(Merchant.is_subscriber.is_(True))
        )
    ).all()

    featured_rows = (
        await session.execute(
            text(
                """
                SELECT
                  COALESCE(l.country_code, '(unknown)') AS country,
                  COALESCE(NULLIF(TRIM(l.city), ''), '(unknown)') AS city,
                  COUNT(*) FILTER (
                    WHERE d.is_active IS TRUE
                      AND d.deleted_at IS NULL
                      AND (d.expires_at IS NULL OR d.expires_at > NOW())
                  )::int AS live,
                  COUNT(*)::int AS total
                FROM deals d
                JOIN merchants m ON m.id = d.merchant_id
                JOIN locations l ON l.id = m.location_id
                WHERE m.is_subscriber IS TRUE
                   OR m.tier_level::text IN ('featured', 'enterprise')
                   OR COALESCE(d.tier_priority_score, 0) >= 200
                   OR COALESCE(d.slot_exempt, false)
                GROUP BY 1, 2
                ORDER BY total DESC
                """
            )
        )
    ).all()

    summary_row = (
        await session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*)::int FROM newsletter_subscribers WHERE is_subscribed IS TRUE) AS newsletter_active,
                  (SELECT COUNT(*)::int FROM merchants WHERE is_subscriber IS TRUE) AS merchant_subs_live,
                  (SELECT COUNT(*)::int FROM merchants WHERE is_subscriber IS TRUE AND subscription_phase = 'trial') AS merchant_trial,
                  (SELECT COUNT(*)::int FROM merchants WHERE is_subscriber IS TRUE AND subscription_phase <> 'trial') AS merchant_paid
                """
            )
        )
    ).one()

    click_total = int(
        (
            await session.execute(
                text("SELECT COUNT(*)::int FROM click_events")
            )
        ).scalar_one()
    )

    live_featured = sum(int(row.live or 0) for row in featured_rows)
    priority_total = sum(int(row.total or 0) for row in featured_rows)

    clicks_by_area = [
        AreaCount(country=str(row.country), city=str(row.city), count=int(row.n))
        for row in click_rows
    ]

    newsletter_by_area: list[AreaCount] = []
    for row in newsletter_rows:
        country = _country_label(row.country_code)
        city = _city_label(row.city) if row.city else _city_label(row.location)
        newsletter_by_area.append(
            AreaCount(country=country, city=city, count=int(row.n))
        )

    merchant_subs_by_area: list[MerchantSubArea] = []
    area_map: dict[tuple[str, str], MerchantSubArea] = {}
    for row in merchant_area_rows:
        country = _country_label(row.country_code)
        city = _city_label(row.city)
        key = (country, city)
        entry = area_map.get(key)
        if entry is None:
            entry = MerchantSubArea(
                country=country,
                city=city,
                subscription_phase=str(row.subscription_phase or ""),
                tier_level=str(getattr(row.tier_level, "value", row.tier_level) or ""),
            )
            area_map[key] = entry
        phase = str(row.subscription_phase or "")
        if phase == "trial":
            entry.trial += 1
        else:
            entry.paid += 1
    merchant_subs_by_area = sorted(
        area_map.values(),
        key=lambda item: item.trial + item.paid,
        reverse=True,
    )

    featured_ads_by_area = [
        FeaturedAdArea(
            country=str(row.country),
            city=str(row.city),
            live=int(row.live or 0),
            priority_deals_total=int(row.total or 0),
        )
        for row in featured_rows
    ]

    return DashboardMetricsRead(
        as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        summary=DashboardMetricsSummary(
            deal_clicks=click_total,
            newsletter_active=int(summary_row.newsletter_active or 0),
            merchant_subs_live=int(summary_row.merchant_subs_live or 0),
            merchant_trial=int(summary_row.merchant_trial or 0),
            merchant_paid=int(summary_row.merchant_paid or 0),
            live_featured_ads=live_featured,
            priority_deals_total=priority_total,
        ),
        clicks_by_area=clicks_by_area,
        newsletter_by_area=newsletter_by_area,
        merchant_subs={
            "trial": int(summary_row.merchant_trial or 0),
            "paid": int(summary_row.merchant_paid or 0),
        },
        merchant_subs_by_area=merchant_subs_by_area,
        featured_ads_by_area=featured_ads_by_area,
    )
