"""Spatial query tests across multiple English-speaking markets.

Unit tests always run. Integration tests that hit PostGIS are marked
``@pytest.mark.spatial`` and skip cleanly when the DB is unavailable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_DistanceSphere, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.location import Location
from app.models.merchant import TierLevel
from app.services.ranking import (
    compute_feed_score,
    freshness_score,
    proximity_score,
    scrape_penalty,
    tier_weight,
)

# Representative city centres for English-speaking markets (lon, lat)
MARKET_POINTS: dict[str, tuple[str, float, float]] = {
    "GB": ("London", -0.1276, 51.5072),
    "US": ("New York", -74.0060, 40.7128),
    "CA": ("Toronto", -79.3832, 43.6532),
    "AU": ("Sydney", 151.2093, -33.8688),
    "IE": ("Dublin", -6.2603, 53.3498),
    "NZ": ("Auckland", 174.7633, -36.8485),
    "SG": ("Singapore", 103.8198, 1.3521),
    "ZA": ("Cape Town", 18.4241, -33.9249),
    "PH": ("Manila", 120.9842, 14.5995),
    "IN": ("Mumbai", 72.8777, 19.0760),
    "AE": ("Dubai", 55.2708, 25.2048),
}


# ---------------------------------------------------------------------------
# Unit tests (no DB)
# ---------------------------------------------------------------------------


def test_tier_weights_enterprise_featured_scraped() -> None:
    assert tier_weight(TierLevel.ENTERPRISE) == 1000.0
    assert tier_weight(TierLevel.FEATURED) == 750.0
    assert tier_weight(TierLevel.FREE) == 0.0


def test_proximity_score_decays_with_distance() -> None:
    near = proximity_score(1.0)
    far = proximity_score(50.0)
    assert near > far
    assert near <= 100.0
    assert proximity_score(0.0) == pytest.approx(100.0, rel=1e-3)


def test_freshness_bonus_higher_for_newer_deals() -> None:
    now = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    fresh = freshness_score(now, now=now)
    stale = freshness_score(
        datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        now=now,
    )
    assert fresh > stale
    assert fresh == pytest.approx(50.0, rel=1e-3)


def test_scrape_penalty_only_for_free_non_subscribers() -> None:
    assert scrape_penalty(is_subscriber=False, tier=TierLevel.FREE) == 200.0
    assert scrape_penalty(is_subscriber=True, tier=TierLevel.FREE) == 0.0
    assert scrape_penalty(is_subscriber=False, tier=TierLevel.ENTERPRISE) == 0.0


def test_feed_score_enterprise_beats_nearby_scraped() -> None:
    now = datetime.now(timezone.utc)
    enterprise = compute_feed_score(
        tier=TierLevel.ENTERPRISE,
        distance_km=40.0,
        created_at=now,
        is_subscriber=True,
        now=now,
    )
    scraped = compute_feed_score(
        tier=TierLevel.FREE,
        distance_km=0.5,
        created_at=now,
        is_subscriber=False,
        now=now,
    )
    assert enterprise > scraped


def test_haversine_like_distance_ordering_logic() -> None:
    """Pure ranking: closer deals outrank farther ones at equal tier."""
    now = datetime.now(timezone.utc)
    close = compute_feed_score(
        tier=TierLevel.FEATURED,
        distance_km=2.0,
        created_at=now,
        is_subscriber=True,
        now=now,
    )
    distant = compute_feed_score(
        tier=TierLevel.FEATURED,
        distance_km=45.0,
        created_at=now,
        is_subscriber=True,
        now=now,
    )
    assert close > distant


# ---------------------------------------------------------------------------
# PostGIS integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def spatial_session(db_url: str, postgis_ready: bool):
    if not postgis_ready:
        pytest.skip("PostGIS database not available")

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    # Create only locations table for isolated spatial tests if missing
    Base.metadata.create_all(bind=engine, tables=[Location.__table__])

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        # Clean previous test rows with known marker timezone
        session.execute(
            text("DELETE FROM locations WHERE timezone = 'test/spatial'")
        )
        session.commit()
        yield session
        session.rollback()
        session.execute(
            text("DELETE FROM locations WHERE timezone = 'test/spatial'")
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()


def _insert_market_locations(session: Session) -> list[Location]:
    rows: list[Location] = []
    for country, (city, lon, lat) in MARKET_POINTS.items():
        loc = Location(
            id=uuid.uuid4(),
            country_code=country,
            city=city,
            timezone="test/spatial",
            latitude=lat,
            longitude=lon,
            geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
        )
        session.add(loc)
        rows.append(loc)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


@pytest.mark.spatial
def test_postgis_extension_enabled(spatial_session: Session) -> None:
    enabled = spatial_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
    ).scalar()
    assert enabled is True


@pytest.mark.spatial
def test_insert_locations_for_multiple_countries(spatial_session: Session) -> None:
    rows = _insert_market_locations(spatial_session)
    assert len(rows) == len(MARKET_POINTS)
    countries = {r.country_code for r in rows}
    assert {"GB", "US", "AU", "SG", "AE"}.issubset(countries)


@pytest.mark.spatial
@pytest.mark.parametrize(
    "country,city,lon,lat",
    [
        ("GB", "London", -0.1276, 51.5072),
        ("US", "New York", -74.0060, 40.7128),
        ("AU", "Sydney", 151.2093, -33.8688),
        ("SG", "Singapore", 103.8198, 1.3521),
        ("AE", "Dubai", 55.2708, 25.2048),
    ],
)
def test_nearby_query_finds_city_in_country(
    spatial_session: Session,
    country: str,
    city: str,
    lon: float,
    lat: float,
) -> None:
    _insert_market_locations(spatial_session)

    # Query from a point ~1–2 km offset from city centre
    query_lon = lon + 0.01
    query_lat = lat + 0.01
    radius_m = 25_000.0

    user_point = ST_SetSRID(ST_MakePoint(query_lon, query_lat), 4326)
    location_geog = cast(Location.geom, Geography)
    user_geog = cast(user_point, Geography)
    distance_km = ST_DistanceSphere(Location.geom, user_point) / 1000.0

    stmt = (
        select(Location, distance_km.label("distance_km"))
        .where(Location.country_code == country)
        .where(ST_DWithin(location_geog, user_geog, radius_m))
        .order_by(distance_km.asc())
    )
    result = spatial_session.execute(stmt).all()
    assert result, f"Expected nearby hit for {city}, {country}"
    loc, dist = result[0]
    assert loc.city == city
    assert loc.country_code == country
    assert float(dist) < 25.0


@pytest.mark.spatial
def test_spatial_query_excludes_far_markets(spatial_session: Session) -> None:
    """A London-radius query must not return Sydney."""
    _insert_market_locations(spatial_session)

    london_lon, london_lat = -0.1276, 51.5072
    user_point = ST_SetSRID(ST_MakePoint(london_lon, london_lat), 4326)
    location_geog = cast(Location.geom, Geography)
    user_geog = cast(user_point, Geography)

    stmt = (
        select(Location)
        .where(ST_DWithin(location_geog, user_geog, 50_000))  # 50 km
    )
    rows = spatial_session.execute(stmt).scalars().all()
    cities = {r.city for r in rows}
    assert "London" in cities
    assert "Sydney" not in cities
    assert "New York" not in cities


@pytest.mark.spatial
def test_distance_sphere_orders_closest_first(spatial_session: Session) -> None:
    _insert_market_locations(spatial_session)

    # Point between London and Dublin — London should still be nearer than NYC
    lon, lat = -3.0, 52.5
    user_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    distance_km = ST_DistanceSphere(Location.geom, user_point) / 1000.0

    stmt = (
        select(Location.city, distance_km.label("distance_km"))
        .where(Location.country_code.in_(["GB", "IE", "US"]))
        .order_by(distance_km.asc())
    )
    ordered = spatial_session.execute(stmt).all()
    assert len(ordered) >= 2
    assert ordered[0][0] in {"London", "Dublin"}
    us_rank = next(i for i, (city, _) in enumerate(ordered) if city == "New York")
    assert us_rank > 0
