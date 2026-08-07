"""Feed ranking: tier weight + proximity + freshness - scrape penalty."""

from __future__ import annotations

from datetime import datetime, timezone
from math import exp

from app.models.merchant import TierLevel

# Tier base weights — paid Priority (€20) maps to FEATURED and always beats scrapes
TIER_WEIGHTS: dict[TierLevel, float] = {
    TierLevel.ENTERPRISE: 1000.0,
    TierLevel.FEATURED: 750.0,  # Priority subscriber slots
    TierLevel.FREE: 0.0,  # scraped / external listings
}

# Distance: max +100 decaying with km
DISTANCE_MAX_BONUS = 100.0
DISTANCE_DECAY_KM = 25.0  # ~e^-1 at 25 km

# Freshness: bonus for recently created deals
FRESHNESS_MAX_BONUS = 50.0
FRESHNESS_HALF_LIFE_HOURS = 72.0

# Strong penalty so scraped external deals sit below paid Priority slots
SCRAPE_PENALTY = 200.0


def tier_weight(tier: TierLevel | str) -> float:
    if isinstance(tier, str):
        tier = TierLevel(tier)
    return TIER_WEIGHTS.get(tier, 0.0)


def proximity_score(distance_km: float | None, *, radius_km: float = 50.0) -> float:
    """
    Distance bonus decaying from DISTANCE_MAX_BONUS at 0 km toward 0 at large distances.

    Deals outside radius_km still receive a tiny residual so ranking remains stable.
    """
    if distance_km is None:
        return 0.0
    if distance_km < 0:
        distance_km = 0.0
    bonus = DISTANCE_MAX_BONUS * exp(-distance_km / DISTANCE_DECAY_KM)
    if distance_km > radius_km:
        bonus *= 0.1
    return bonus


def freshness_score(created_at: datetime | None, *, now: datetime | None = None) -> float:
    """Exponential decay freshness bonus based on deal age."""
    if created_at is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_hours = max((now - created_at).total_seconds() / 3600.0, 0.0)
    # half-life decay: bonus = max * 0.5^(age / half_life)
    return FRESHNESS_MAX_BONUS * (0.5 ** (age_hours / FRESHNESS_HALF_LIFE_HOURS))


def scrape_penalty(*, is_subscriber: bool, tier: TierLevel | str) -> float:
    """Apply a small penalty to non-subscriber scraped inventory."""
    if isinstance(tier, str):
        tier = TierLevel(tier)
    if is_subscriber or tier != TierLevel.FREE:
        return 0.0
    return SCRAPE_PENALTY


def compute_feed_score(
    *,
    tier: TierLevel | str,
    distance_km: float | None,
    created_at: datetime | None,
    is_subscriber: bool = False,
    radius_km: float = 50.0,
    tier_priority_score: int = 0,
    now: datetime | None = None,
) -> float:
    """
    Score = tier weight + proximity + freshness - scrape penalty + manual priority.

    Higher is better for feed ordering.
    """
    score = (
        tier_weight(tier)
        + proximity_score(distance_km, radius_km=radius_km)
        + freshness_score(created_at, now=now)
        - scrape_penalty(is_subscriber=is_subscriber, tier=tier)
        + float(tier_priority_score)
    )
    return round(score, 4)
