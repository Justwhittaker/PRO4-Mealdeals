"""Geo / location helper endpoints."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_DistanceSphere, ST_MakePoint, ST_SetSRID
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import cast, func, select

from app.api.dependencies import DbSession
from app.models.location import Location
from app.scrapers.markets import MARKET_CITIES, TARGET_MARKETS
from app.services.ingest import CITY_COORDS, normalize_country

router = APIRouter(prefix="/geo", tags=["geo"])


class MarketCityRead(BaseModel):
    city: str
    city_slug: str


class MarketCountryRead(BaseModel):
    iso: str
    country_slug: str
    cities: list[MarketCityRead]


def _city_slug(city: str) -> str:
    return city.strip().lower().replace(" ", "-")


@router.get("/markets", response_model=list[MarketCountryRead])
async def list_markets() -> list[MarketCountryRead]:
    """All scrape TARGET_MARKETS with nested cities (for country search UI)."""
    out: list[MarketCountryRead] = []
    for iso in TARGET_MARKETS:
        cities = MARKET_CITIES.get(iso) or []
        slug = "uk" if iso == "GB" else iso.lower()
        out.append(
            MarketCountryRead(
                iso=iso,
                country_slug=slug,
                cities=[
                    MarketCityRead(city=c, city_slug=_city_slug(c)) for c in cities
                ],
            )
        )
    return out



def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class ResolvedArea(BaseModel):
    country_code: str
    country_slug: str
    city: str
    city_slug: str
    latitude: float
    longitude: float
    distance_km: float


class LocationCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    city: str = Field(..., max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    country_code: str
    city: str
    timezone: str
    latitude: float
    longitude: float


class NearbyLocation(LocationRead):
    distance_km: float


@router.get("/resolve", response_model=ResolvedArea)
async def resolve_area(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> ResolvedArea:
    """
    Map browser GPS / IP coordinates to the nearest supported MealDeals city.

    Used for auto-geolocation when edge geo headers are missing.
    """
    best_key: tuple[str, str] | None = None
    best_dist = float("inf")
    best_coords = (0.0, 0.0)
    for (country, city), (clat, clon) in CITY_COORDS.items():
        dist = _haversine_km(lat, lon, clat, clon)
        if dist < best_dist:
            best_dist = dist
            best_key = (country, city)
            best_coords = (clat, clon)

    if best_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No supported cities configured",
        )

    country_iso, city = best_key
    country_iso = normalize_country(country_iso)
    country_slug = "uk" if country_iso == "GB" else country_iso.lower()
    city_slug = city.lower().replace(" ", "-")
    return ResolvedArea(
        country_code=country_iso,
        country_slug=country_slug,
        city=city,
        city_slug=city_slug,
        latitude=best_coords[0],
        longitude=best_coords[1],
        distance_km=round(best_dist, 1),
    )


@router.post("/locations", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(payload: LocationCreate, db: DbSession) -> Location:
    point = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)
    location = Location(
        country_code=payload.country_code.upper(),
        city=payload.city,
        timezone=payload.timezone,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geom=point,
    )
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


@router.get("/locations", response_model=list[LocationRead])
async def list_locations(
    db: DbSession,
    country_code: str | None = Query(default=None, min_length=2, max_length=2),
    city: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Location]:
    stmt = select(Location).limit(limit)
    if country_code:
        stmt = stmt.where(Location.country_code == country_code.upper())
    if city:
        stmt = stmt.where(func.lower(Location.city) == city.lower())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/locations/nearby", response_model=list[NearbyLocation])
async def nearby_locations(
    db: DbSession,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=25.0, gt=0, le=500),
    country_code: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[NearbyLocation]:
    """
    PostGIS nearby search using geography distance in metres.

    ST_DWithin on geography uses metres; we convert km → m.
    """
    radius_m = radius_km * 1000.0
    user_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    # Cast to geography so ST_DWithin uses metres (not degrees)
    location_geog = cast(Location.geom, Geography)
    user_geog = cast(user_point, Geography)
    distance_m = ST_DistanceSphere(Location.geom, user_point)

    stmt = (
        select(Location, (distance_m / 1000.0).label("distance_km"))
        .where(ST_DWithin(location_geog, user_geog, radius_m))
        .order_by(distance_m.asc())
        .limit(limit)
    )
    if country_code:
        stmt = stmt.where(Location.country_code == country_code.upper())

    result = await db.execute(stmt)
    rows = result.all()
    return [
        NearbyLocation(
            id=loc.id,
            country_code=loc.country_code,
            city=loc.city,
            timezone=loc.timezone,
            latitude=loc.latitude,
            longitude=loc.longitude,
            distance_km=round(float(dist), 3),
        )
        for loc, dist in rows
    ]


@router.get("/locations/{location_id}", response_model=LocationRead)
async def get_location(location_id: UUID, db: DbSession) -> Location:
    location = await db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location
