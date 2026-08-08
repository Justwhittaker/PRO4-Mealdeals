"""Deal feed and value-calculator endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from geoalchemy2.functions import ST_DistanceSphere, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrencySvc, DbSession
from app.models.deal import Deal, DealItem
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import PAID_DEAL_SLOT_LIMIT, Merchant
from app.models.translation import DealTranslation
from app.schemas.deal import (
    DealCreate,
    DealDetailRead,
    DealFeedItem,
    DealFeedResponse,
    DealRead,
    DealUpdate,
    ValueCalculatorResponse,
)
from app.services.affiliate import build_affiliate_urls
from app.services.deal_copy import clean_deal_description
from app.services.ingest import normalize_city, normalize_country
from app.services.ranking import compute_feed_score
from app.services.scrape_runner import scrape_and_ingest_area

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(payload: DealCreate, db: DbSession) -> Deal:
    merchant = await db.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merchant_id does not exist",
        )

    # Priority slot rules apply only to non–slot-exempt deals (designed specials skip).
    if not payload.slot_exempt:
        slot_limit = merchant.deal_slot_limit or 0
        if not merchant.is_subscriber or slot_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Priority deal slots require an active subscription "
                    "(€20 for 3 months / then €20 per month — 3 slots)."
                ),
            )

        active_count = (
            await db.execute(
                select(func.count())
                .select_from(Deal)
                .where(
                    Deal.merchant_id == merchant.id,
                    Deal.is_active.is_(True),
                    Deal.slot_exempt.is_(False),
                )
            )
        ).scalar_one()
        if active_count >= slot_limit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Deal slot limit reached ({active_count}/{slot_limit}). "
                    f"Paid plans include {PAID_DEAL_SLOT_LIMIT} active priority deals."
                ),
            )

    # Paid merchant deals get a ranking boost so they sit above scrapes
    priority = payload.tier_priority_score or 200

    clean_url = payload.clean_url
    affiliate_url = payload.affiliate_url
    if payload.scraped_raw_url and (not clean_url or not affiliate_url):
        generated_clean, generated_aff = build_affiliate_urls(payload.scraped_raw_url)
        clean_url = clean_url or generated_clean
        affiliate_url = affiliate_url or generated_aff

    deal = Deal(
        merchant_id=payload.merchant_id,
        scraped_raw_url=payload.scraped_raw_url,
        clean_url=clean_url,
        affiliate_url=affiliate_url,
        original_price=payload.original_price,
        deal_price=payload.deal_price,
        currency_code=payload.currency_code.upper(),
        is_active=payload.is_active,
        tier_priority_score=priority,
        slot_exempt=payload.slot_exempt,
        image_url=payload.image_url,
        expires_at=payload.expires_at,
    )
    db.add(deal)
    await db.flush()

    for item in payload.items:
        db.add(
            DealItem(
                deal_id=deal.id,
                category=item.category,
                item_name=item.item_name,
                individual_price=item.individual_price,
            )
        )

    if payload.title or payload.description:
        title = (payload.title or payload.description or "")[:255]
        db.add(
            DealTranslation(
                deal_id=deal.id,
                language_code=payload.language_code,
                title=title,
                description=payload.description or payload.title or "",
            )
        )

    await db.flush()
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    return loaded.scalar_one()


@router.get("/feed", response_model=DealFeedResponse)
async def deals_feed(
    db: DbSession,
    currency_svc: CurrencySvc,
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
    city: str | None = Query(default=None),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    radius_miles: float | None = Query(
        default=None,
        gt=0,
        le=300,
        description="Search radius in miles (25 / 50 / 100 / 150). Overrides radius_km.",
    ),
    sort: str = Query(
        default="score",
        description="score = featured/priority first; distance = nearest first",
    ),
    currency_override: str | None = Query(default=None, min_length=3, max_length=3),
    language_code: str = Query(default="en", min_length=2, max_length=5),
    limit: int = Query(default=50, ge=1, le=10000),
    auto_scrape: bool = Query(
        default=True,
        description="When the area feed is empty, skim the net and ingest deals.",
    ),
) -> DealFeedResponse:
    """
    Geo-aware deal feed.

    - country only → nationwide for that country
    - city → that city (exact name); with lat/lon + radius also includes nearby
    - lat/lon + radius (no city) → circle search for geo homepage-style feeds
    Sort: score (featured first) or distance (needs lat/lon).
    """
    if country_code:
        country_code = normalize_country(country_code)
    if city:
        city = normalize_city(city)

    if radius_miles is not None:
        effective_radius_km = float(radius_miles) * 1.60934
    elif radius_km is not None:
        effective_radius_km = float(radius_km)
    else:
        # Default ~25 miles
        effective_radius_km = 25.0 * 1.60934

    sort_mode = sort.lower().strip()
    if sort_mode not in {"score", "distance"}:
        sort_mode = "score"

    now = datetime.now(timezone.utc)
    has_point = lat is not None and lon is not None

    distance_expr = None
    if has_point:
        user_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        distance_expr = ST_DistanceSphere(Location.geom, user_point) / 1000.0

    columns = [Deal, Merchant, Location]
    if distance_expr is not None:
        columns.append(distance_expr.label("distance_km"))

    stmt = (
        select(*columns)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(Deal.is_active.is_(True))
        .where(or_(Deal.expires_at.is_(None), Deal.expires_at > now))
        .options(
            selectinload(Deal.items),
            selectinload(Deal.translations),
        )
    )

    if country_code:
        stmt = stmt.where(Location.country_code == country_code.upper())

    radius_explicit = radius_miles is not None or radius_km is not None

    # City pages: always pin to that city. When lat/lon + radius are also sent,
    # include nearby venues inside the circle (still not the whole country).
    # Country / geo radius mode (no city): filter by distance only.
    if city and has_point and distance_expr is not None and radius_explicit:
        stmt = stmt.where(
            or_(
                Location.city.ilike(city),
                distance_expr <= effective_radius_km,
            )
        )
    elif city:
        stmt = stmt.where(Location.city.ilike(city))
    elif has_point and distance_expr is not None:
        stmt = stmt.where(distance_expr <= effective_radius_km)

    stmt = stmt.limit(limit * 3)  # over-fetch then rank in Python for scoring clarity
    result = await db.execute(stmt)
    rows = result.unique().all()

    feed_items: list[DealFeedItem] = []
    override = currency_override.upper() if currency_override else None

    for row in rows:
        if has_point:
            deal, merchant, location, distance_km = row
            distance_km = float(distance_km) if distance_km is not None else None
        else:
            deal, merchant, location = row
            distance_km = None

        score = compute_feed_score(
            tier=merchant.tier_level,
            distance_km=distance_km,
            created_at=deal.created_at,
            is_subscriber=merchant.is_subscriber,
            radius_km=effective_radius_km,
            tier_priority_score=deal.tier_priority_score,
            now=now,
        )

        translation = next(
            (t for t in deal.translations if t.language_code == language_code),
            deal.translations[0] if deal.translations else None,
        )

        converted_price: Decimal | None = None
        converted_currency: str | None = None
        if override and override != deal.currency_code:
            converted_price = await currency_svc.convert(
                deal.deal_price, deal.currency_code, override
            )
            if converted_price is not None:
                converted_currency = override

        feed_items.append(
            DealFeedItem(
                id=deal.id,
                merchant_id=merchant.id,
                merchant_name=merchant.name,
                title=translation.title if translation else None,
                description=clean_deal_description(
                    translation.description if translation else None
                ),
                original_price=deal.original_price,
                deal_price=deal.deal_price,
                currency_code=deal.currency_code,
                converted_deal_price=converted_price,
                converted_currency=converted_currency,
                distance_km=round(distance_km, 3) if distance_km is not None else None,
                feed_score=score,
                affiliate_url=deal.affiliate_url,
                clean_url=deal.clean_url,
                image_url=deal.image_url,
                logo_url=merchant.logo_url,
                created_at=deal.created_at,
                expires_at=deal.expires_at,
                city=location.city,
                country_code=location.country_code,
                tier_level=merchant.tier_level,
                is_subscriber=merchant.is_subscriber,
            )
        )

    if sort_mode == "distance" and has_point:
        feed_items.sort(
            key=lambda item: (
                item.distance_km is None,
                item.distance_km if item.distance_km is not None else 1e9,
                -item.feed_score,
            )
        )
    else:
        feed_items.sort(key=lambda item: item.feed_score, reverse=True)
    feed_items = feed_items[:limit]

    # Auto-skim the net for this area when visitors hit an empty city feed
    if auto_scrape and not feed_items and country_code and city:
        await asyncio.to_thread(scrape_and_ingest_area, country_code, city)
        return await deals_feed(
            db=db,
            currency_svc=currency_svc,
            country_code=country_code,
            city=city,
            lat=lat,
            lon=lon,
            radius_km=effective_radius_km,
            radius_miles=None,
            sort=sort_mode,
            currency_override=currency_override,
            language_code=language_code,
            limit=limit,
            auto_scrape=False,
        )

    return DealFeedResponse(count=len(feed_items), results=feed_items)


@router.patch("/{deal_id}", response_model=DealRead)
async def update_deal(
    deal_id: UUID,
    payload: DealUpdate,
    db: DbSession,
) -> Deal:
    """Toggle active / edit a deal. Deactivating frees a Priority slot but keeps history."""
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    fields_set = payload.model_fields_set
    data = payload.model_dump(exclude_unset=True)
    reactivating = (
        data.get("is_active") is True
        and not deal.is_active
        and not deal.slot_exempt
    )
    if reactivating:
        merchant = await db.get(Merchant, deal.merchant_id)
        slot_limit = (merchant.deal_slot_limit if merchant else 0) or 0
        if merchant is None or not merchant.is_subscriber or slot_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Priority deal slots require an active subscription "
                    "(€20 for 3 months / then €20 per month — 3 slots)."
                ),
            )
        active_count = (
            await db.execute(
                select(func.count())
                .select_from(Deal)
                .where(
                    Deal.merchant_id == deal.merchant_id,
                    Deal.is_active.is_(True),
                    Deal.slot_exempt.is_(False),
                )
            )
        ).scalar_one()
        if active_count >= slot_limit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Deal slot limit reached ({active_count}/{slot_limit}). "
                    "Deactivate another Priority deal first."
                ),
            )

    items_payload = payload.items if "items" in fields_set else None
    title = payload.title if "title" in fields_set else None
    description = payload.description if "description" in fields_set else None
    language_code = (
        payload.language_code
        if "language_code" in fields_set and payload.language_code
        else "en"
    )
    data.pop("items", None)
    data.pop("title", None)
    data.pop("description", None)
    data.pop("language_code", None)

    if "currency_code" in data and data["currency_code"]:
        data["currency_code"] = str(data["currency_code"]).upper()

    for field, value in data.items():
        if hasattr(deal, field):
            setattr(deal, field, value)

    if title is not None or description is not None:
        translation = next(
            (t for t in deal.translations if t.language_code == language_code),
            None,
        )
        if translation is None and deal.translations:
            translation = deal.translations[0]
        next_title = (
            (title if title is not None else (translation.title if translation else ""))
            or (description or "")
        )[:255]
        next_description = (
            description
            if description is not None
            else (translation.description if translation else title or "")
        )
        if translation is None:
            db.add(
                DealTranslation(
                    deal_id=deal.id,
                    language_code=language_code,
                    title=next_title,
                    description=next_description or next_title,
                )
            )
        else:
            if title is not None:
                translation.title = next_title
            if description is not None:
                translation.description = next_description or next_title
            elif title is not None and not translation.description:
                translation.description = next_title

    if items_payload is not None:
        for existing in list(deal.items):
            await db.delete(existing)
        await db.flush()
        for item in items_payload:
            db.add(
                DealItem(
                    deal_id=deal.id,
                    category=item.category,
                    item_name=item.item_name,
                    individual_price=item.individual_price,
                )
            )

    await db.flush()
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    return loaded.scalar_one()


@router.get("/{deal_id}", response_model=DealDetailRead)
async def get_deal(deal_id: UUID, db: DbSession) -> DealDetailRead:
    result = await db.execute(
        select(Deal, Merchant, Location)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    row = result.unique().one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    deal, merchant, location = row
    about_blurb = merchant.bio
    if not about_blurb:
        # Fall back to marketing contact ledger from prior scrapes.
        contact = (
            await db.execute(
                select(MarketingContact.about_blurb)
                .where(
                    MarketingContact.country_code == location.country_code,
                    func.lower(MarketingContact.business_name)
                    == merchant.name.lower(),
                    MarketingContact.about_blurb.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        about_blurb = contact
    return DealDetailRead(
        id=deal.id,
        merchant_id=deal.merchant_id,
        reposted_from_id=deal.reposted_from_id,
        scraped_raw_url=deal.scraped_raw_url,
        clean_url=deal.clean_url,
        affiliate_url=deal.affiliate_url,
        original_price=deal.original_price,
        deal_price=deal.deal_price,
        currency_code=deal.currency_code,
        is_active=deal.is_active,
        tier_priority_score=deal.tier_priority_score,
        slot_exempt=deal.slot_exempt,
        image_url=deal.image_url,
        expires_at=deal.expires_at,
        created_at=deal.created_at,
        items=list(deal.items),
        translations=list(deal.translations),
        merchant_name=merchant.name,
        logo_url=merchant.logo_url,
        about_blurb=about_blurb,
        tier_level=merchant.tier_level,
        is_subscriber=merchant.is_subscriber,
        city=location.city,
        country_code=location.country_code,
    )


@router.get("/{deal_id}/value-calculator", response_model=ValueCalculatorResponse)
async def value_calculator(deal_id: UUID, db: DbSession) -> ValueCalculatorResponse:
    """SUM(individual_price) - deal_price and savings percentage."""
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.items))
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    items_total = sum((item.individual_price for item in deal.items), Decimal("0.00"))
    savings_amount = items_total - deal.deal_price
    if items_total > 0:
        savings_percent = float((savings_amount / items_total) * Decimal("100"))
    else:
        savings_percent = 0.0

    return ValueCalculatorResponse(
        deal_id=deal.id,
        deal_price=deal.deal_price,
        items_total=items_total,
        savings_amount=savings_amount,
        savings_percent=round(savings_percent, 2),
        currency_code=deal.currency_code,
        items=deal.items,
    )
