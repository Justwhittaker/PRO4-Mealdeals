"""Live product metrics for staff dashboards."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AreaCount(BaseModel):
    country: str
    city: str
    count: int


class MerchantSubArea(BaseModel):
    country: str
    city: str
    trial: int = 0
    paid: int = 0
    subscription_phase: str = ""
    tier_level: str = ""


class FeaturedAdArea(BaseModel):
    country: str
    city: str
    live: int
    priority_deals_total: int


class DashboardMetricsSummary(BaseModel):
    deal_clicks: int
    newsletter_active: int
    merchant_subs_live: int
    merchant_trial: int
    merchant_paid: int
    live_featured_ads: int
    priority_deals_total: int


class DashboardMetricsRead(BaseModel):
    as_of: str
    source: str = "postgres"
    page_visits_note: str = Field(
        default=(
            "Page visits are tracked by Vercel Web Analytics (not stored in Postgres). "
            "Open the Vercel project Analytics tab after production deploy."
        ),
    )
    vercel_analytics_url: str = "https://vercel.com/justin-whittakers-projects/dineadeal/analytics"
    summary: DashboardMetricsSummary
    clicks_by_area: list[AreaCount]
    newsletter_by_area: list[AreaCount]
    merchant_subs: dict[str, int]
    merchant_subs_by_area: list[MerchantSubArea]
    featured_ads_by_area: list[FeaturedAdArea]
