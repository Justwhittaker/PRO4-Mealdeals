"""Deal feed and value-calculator endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from geoalchemy2.functions import ST_DistanceSphere, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrencySvc, DbSession
from app.core.feed_limits import (
    MAX_FEED_CANDIDATES,
    MAX_FEED_LIMIT,
    MAX_SITEMAP_LIMIT,
)
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
    DealSitemapEntry,
    DealTranslationRead,
    DealSitemapResponse,
    DealUpdate,
    ValueCalculatorResponse,
)
from app.services.affiliate import build_affiliate_urls
from app.services.deal_copy import clean_deal_description
from app.services.deal_link import LinkKind, cta_label_for_link, outbound_link_meta
from app.services.listing_quality import is_policy_violation, prepare_public_listing
from app.services.ingest import normalize_city, normalize_country
from app.services.ranking import compute_feed_score
from app.services.scrape_runner import scrape_and_ingest_area
from app.scrapers.categories import venue_category_id

router = APIRouter(prefix="/deals", tags=["deals"])


def _public_link_fields(
    deal: Deal,
    merchant_name: str,
) -> dict[str, str | LinkKind | None]:
    outbound, link_kind = outbound_link_meta(
        affiliate_url=deal.affiliate_url,
        clean_url=deal.clean_url,
        scraped_raw_url=deal.scraped_raw_url,
    )
    return {
        "outbound_url": outbound,
        "link_kind": link_kind,
        "cta_label": cta_label_for_link(link_kind, merchant_name),
    }


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
async def create_deal(payload: DealCreate, db: DbSession) -> Deal:
    merchant = await db.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merchant_id does not exist",
        )

    # Priority slot rules apply only when activating a live Priority deal.
    if not payload.slot_exempt and payload.is_active:
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
                    Deal.deleted_at.is_(None),
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
    elif not payload.slot_exempt:
        # Save-for-later still requires a Priority subscription.
        slot_limit = merchant.deal_slot_limit or 0
        if not merchant.is_subscriber or slot_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Priority deal drafts require an active subscription "
                    "(€20 for 3 months / then €20 per month — 3 slots)."
                ),
            )

    # Paid merchant deals get a ranking boost so they sit above scrapes
    priority = payload.tier_priority_score or 200

    image_url = payload.image_url
    if image_url is not None:
        image_url = image_url.strip() or None
        if image_url and image_url.startswith("data:") and len(image_url) > 1_500_000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "Deal photo is too large to store. Use a smaller image "
                    "or an https:// image URL."
                ),
            )

    clean_url = payload.clean_url
    affiliate_url = payload.affiliate_url
    if payload.scraped_raw_url and (not clean_url or not affiliate_url):
        generated_clean, generated_aff = build_affiliate_urls(payload.scraped_raw_url)
        clean_url = clean_url or generated_clean
        affiliate_url = affiliate_url or generated_aff

    if not (payload.venue_category and str(payload.venue_category).strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="venue_category is required (choose a browse category for this deal).",
        )
    # Honor the merchant's selection; do not re-infer from the business name.
    resolved_category = venue_category_id(str(payload.venue_category).strip())

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
        image_url=image_url,
        venue_category=resolved_category,
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
    category: str | None = Query(
        default=None,
        description="Parent venue category id (e.g. restaurants-cafes-bistros).",
    ),
    limit: int = Query(default=50, ge=1, le=MAX_FEED_LIMIT),
    offset: int = Query(default=0, ge=0),
    auto_scrape: bool = Query(
        default=True,
        description="When the area feed is empty, skim the net and ingest deals.",
    ),
) -> DealFeedResponse:
    """
    Geo-aware deal feed with offset pagination.

    Scores all matching candidates with a lightweight query, then hydrates
    only the requested page so large markets can be browsed without OOM.
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

    category_filter = (category or "").strip().lower() or None
    if category_filter in {"", "all"}:
        category_filter = None

    now = datetime.now(timezone.utc)
    has_point = lat is not None and lon is not None

    distance_expr = None
    if has_point:
        user_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        distance_expr = ST_DistanceSphere(Location.geom, user_point) / 1000.0

    # Phase 1: score lightweight candidates (no translations / images).
    candidate_cols = [
        Deal.id,
        Deal.created_at,
        Deal.tier_priority_score,
        Deal.venue_category,
        Merchant.tier_level,
        Merchant.is_subscriber,
        Merchant.name,
    ]
    if distance_expr is not None:
        candidate_cols.append(distance_expr.label("distance_km"))

    listing_title_col = (
        select(DealTranslation.title)
        .where(
            DealTranslation.deal_id == Deal.id,
            DealTranslation.language_code == "en",
        )
        .limit(1)
        .scalar_subquery()
    )
    candidate_cols.append(listing_title_col.label("listing_title"))

    candidate_stmt = (
        select(*candidate_cols)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(Deal.is_active.is_(True))
        .where(Deal.deleted_at.is_(None))
        .where(or_(Deal.expires_at.is_(None), Deal.expires_at > now))
    )

    if country_code:
        candidate_stmt = candidate_stmt.where(
            Location.country_code == country_code.upper()
        )

    radius_explicit = radius_miles is not None or radius_km is not None

    # City pages: always pin to that city. When lat/lon + radius are also sent,
    # include nearby venues inside the circle (still not the whole country).
    # Country / geo radius mode (no city): filter by distance only.
    if city and has_point and distance_expr is not None and radius_explicit:
        candidate_stmt = candidate_stmt.where(
            or_(
                Location.city.ilike(city),
                distance_expr <= effective_radius_km,
            )
        )
    elif city:
        candidate_stmt = candidate_stmt.where(Location.city.ilike(city))
    elif has_point and distance_expr is not None:
        candidate_stmt = candidate_stmt.where(distance_expr <= effective_radius_km)

    candidate_stmt = candidate_stmt.limit(MAX_FEED_CANDIDATES)
    candidate_rows = (await db.execute(candidate_stmt)).all()

    ranked: list[tuple[UUID, float, float | None]] = []
    for row in candidate_rows:
        if has_point:
            (
                deal_id,
                created_at,
                tier_priority_score,
                venue_category,
                tier_level,
                is_subscriber,
                merchant_name,
                distance_km,
                listing_title,
            ) = row
            distance_km = float(distance_km) if distance_km is not None else None
        else:
            (
                deal_id,
                created_at,
                tier_priority_score,
                venue_category,
                tier_level,
                is_subscriber,
                merchant_name,
                listing_title,
            ) = row
            distance_km = None

        if is_policy_violation(listing_title, merchant_name):
            continue

        parent_category = venue_category_id(
            venue_category,
            merchant_name=merchant_name or "",
        )
        if category_filter and parent_category != category_filter:
            continue

        score = compute_feed_score(
            tier=tier_level,
            distance_km=distance_km,
            created_at=created_at,
            is_subscriber=bool(is_subscriber),
            radius_km=effective_radius_km,
            tier_priority_score=int(tier_priority_score or 0),
            now=now,
        )
        ranked.append((deal_id, score, distance_km))

    if sort_mode == "distance" and has_point:
        ranked.sort(
            key=lambda item: (
                item[2] is None,
                item[2] if item[2] is not None else 1e9,
                -item[1],
            )
        )
    else:
        ranked.sort(key=lambda item: item[1], reverse=True)

    total = len(ranked)
    page = ranked[offset : offset + limit]
    page_ids = [deal_id for deal_id, _score, _distance in page]
    score_by_id = {deal_id: score for deal_id, score, _distance in page}
    distance_by_id = {deal_id: distance for deal_id, _score, distance in page}

    # Auto-skim the net for this area when visitors hit an empty city feed
    if auto_scrape and total == 0 and country_code and city:
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
            category=category_filter,
            limit=limit,
            offset=offset,
            auto_scrape=False,
        )

    feed_items: list[DealFeedItem] = []
    if page_ids:
        hydrate_stmt = (
            select(Deal, Merchant, Location)
            .join(Merchant, Deal.merchant_id == Merchant.id)
            .join(Location, Merchant.location_id == Location.id)
            .where(Deal.id.in_(page_ids))
            .options(selectinload(Deal.translations))
        )
        hydrated = {
            deal.id: (deal, merchant, location)
            for deal, merchant, location in (await db.execute(hydrate_stmt)).unique().all()
        }
        override = currency_override.upper() if currency_override else None
        for deal_id in page_ids:
            packed = hydrated.get(deal_id)
            if packed is None:
                continue
            deal, merchant, location = packed
            distance_km = distance_by_id.get(deal_id)
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

            link_fields = _public_link_fields(deal, merchant.name)
            category_id = (
                venue_category_id(deal.venue_category)
                if deal.venue_category
                else venue_category_id(None, merchant_name=merchant.name)
            )
            public = prepare_public_listing(
                title=translation.title if translation else None,
                description=translation.description if translation else None,
                merchant=merchant.name,
                city=location.city,
                venue_category=category_id,
                is_subscriber=bool(merchant.is_subscriber),
                deal_price=deal.deal_price,
                original_price=deal.original_price,
            )
            if public["blocked"]:
                continue
            feed_items.append(
                DealFeedItem(
                    id=deal.id,
                    merchant_id=merchant.id,
                    merchant_name=merchant.name,
                    title=str(public["title"]) if public["title"] else None,
                    description=clean_deal_description(
                        str(public["description"]) if public["description"] else None
                    ),
                    original_price=Decimal(str(public["original_price"])),
                    deal_price=Decimal(str(public["deal_price"])),
                    currency_code=deal.currency_code,
                    converted_deal_price=converted_price,
                    converted_currency=converted_currency,
                    distance_km=(
                        round(distance_km, 3) if distance_km is not None else None
                    ),
                    feed_score=score_by_id.get(deal_id, 0.0),
                    affiliate_url=deal.affiliate_url,
                    clean_url=deal.clean_url,
                    image_url=deal.image_url,
                    logo_url=merchant.logo_url,
                    venue_category=category_id,
                    created_at=deal.created_at,
                    expires_at=deal.expires_at,
                    city=location.city,
                    area_local=location.area_local,
                    country_code=location.country_code,
                    tier_level=merchant.tier_level,
                    is_subscriber=merchant.is_subscriber,
                    **link_fields,
                )
            )

    return DealFeedResponse(
        count=len(feed_items),
        total=total,
        offset=offset,
        limit=limit,
        results=feed_items,
    )


@router.get("/sitemap", response_model=DealSitemapResponse)
async def deals_sitemap(
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=MAX_SITEMAP_LIMIT),
) -> DealSitemapResponse:
    """
    Lightweight paginated deal URLs for sitemap generation.

    Avoids the ranked feed path (no items/translations/scoring) so sitemap
    builds do not OOM the web service.
    """
    now = datetime.now(timezone.utc)
    active = (
        Deal.is_active.is_(True)
        & Deal.deleted_at.is_(None)
        & or_(Deal.expires_at.is_(None), Deal.expires_at > now)
    )
    listing_title = (
        select(DealTranslation.title)
        .where(
            DealTranslation.deal_id == Deal.id,
            DealTranslation.language_code == "en",
        )
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(
            Deal.id,
            Location.country_code,
            Location.city,
            Deal.created_at,
            listing_title.label("listing_title"),
            Merchant.name,
        )
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(active)
        .order_by(Deal.created_at.desc(), Deal.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    results = [
        DealSitemapEntry(
            id=deal_id,
            country_code=country_code,
            city=city,
            created_at=created_at,
        )
        for deal_id, country_code, city, created_at, title, merchant_name in rows
        if not is_policy_violation(title, merchant_name)
    ]
    total = int(
        await db.scalar(select(func.count()).select_from(Deal).where(active)) or 0
    )
    return DealSitemapResponse(
        count=len(results),
        total=total,
        offset=offset,
        results=results,
    )


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
    if deal is None or deal.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    fields_set = payload.model_fields_set
    data = payload.model_dump(exclude_unset=True)

    if data.pop("remove_from_profile", None) is True:
        deal.deleted_at = datetime.now(timezone.utc)
        deal.is_active = False
        await db.flush()
        loaded = await db.execute(
            select(Deal)
            .where(Deal.id == deal.id)
            .options(selectinload(Deal.items), selectinload(Deal.translations))
        )
        return loaded.scalar_one()

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
                    Deal.deleted_at.is_(None),
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

    if "image_url" in data and data["image_url"] is not None:
        image_url = str(data["image_url"]).strip() or None
        if image_url and image_url.startswith("data:") and len(image_url) > 1_500_000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "Deal photo is too large to store. Use a smaller image "
                    "or an https:// image URL."
                ),
            )
        data["image_url"] = image_url

    if "venue_category" in data:
        raw_cat = data.get("venue_category")
        if raw_cat is None or not str(raw_cat).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="venue_category cannot be empty.",
            )
        # Honor explicit selection — do not override from merchant name.
        data["venue_category"] = venue_category_id(str(raw_cat).strip())

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


@router.post(
    "/{deal_id}/remove-from-profile",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_deal_from_profile(deal_id: UUID, db: DbSession) -> Response:
    """Soft-delete via POST (avoids DELETE 405 on some hosts). Keeps analytics row."""
    deal = await db.get(Deal, deal_id)
    if deal is None or deal.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    deal.deleted_at = datetime.now(timezone.utc)
    deal.is_active = False
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_deal(deal_id: UUID, db: DbSession) -> Response:
    """Soft-delete a deal: hide from profile/feed, keep the row for analytics."""
    deal = await db.get(Deal, deal_id)
    if deal is None or deal.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    deal.deleted_at = datetime.now(timezone.utc)
    deal.is_active = False
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    if deal.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    primary_translation = next(
        (item for item in deal.translations if item.language_code == "en"),
        deal.translations[0] if deal.translations else None,
    )
    category_id = (
        venue_category_id(deal.venue_category)
        if deal.venue_category
        else venue_category_id(None, merchant_name=merchant.name)
    )
    public = prepare_public_listing(
        title=primary_translation.title if primary_translation else None,
        description=primary_translation.description if primary_translation else None,
        merchant=merchant.name,
        city=location.city,
        venue_category=category_id,
        is_subscriber=bool(merchant.is_subscriber),
        deal_price=deal.deal_price,
        original_price=deal.original_price,
        about=merchant.bio,
    )
    if public["blocked"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    public_translations = [
        DealTranslationRead(
            language_code=item.language_code,
            title=(
                str(public["title"])
                if item.language_code == (primary_translation.language_code if primary_translation else "en")
                else item.title
            ),
            description=(
                str(public["description"] or "")
                if item.language_code == (primary_translation.language_code if primary_translation else "en")
                else item.description
            ),
        )
        for item in deal.translations
    ]
    if not public_translations and public["title"]:
        public_translations.append(
            DealTranslationRead(
                language_code="en",
                title=str(public["title"]),
                description=str(public["description"] or ""),
            )
        )
    about_blurb = public["about"] if isinstance(public["about"], str) else None
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
        if contact and not is_policy_violation(contact):
            about_blurb = contact
    link_fields = _public_link_fields(deal, merchant.name)
    return DealDetailRead(
        id=deal.id,
        merchant_id=deal.merchant_id,
        reposted_from_id=deal.reposted_from_id,
        scraped_raw_url=deal.scraped_raw_url,
        clean_url=deal.clean_url,
        affiliate_url=deal.affiliate_url,
        original_price=Decimal(str(public["original_price"])),
        deal_price=Decimal(str(public["deal_price"])),
        currency_code=deal.currency_code,
        is_active=deal.is_active,
        tier_priority_score=deal.tier_priority_score,
        slot_exempt=deal.slot_exempt,
        image_url=deal.image_url,
        venue_category=category_id,
        expires_at=deal.expires_at,
        created_at=deal.created_at,
        items=list(deal.items),
        translations=public_translations,
        merchant_name=merchant.name,
        logo_url=merchant.logo_url,
        about_blurb=about_blurb,
        tier_level=merchant.tier_level,
        is_subscriber=merchant.is_subscriber,
        city=location.city,
        area_local=location.area_local,
        country_code=location.country_code,
        **link_fields,
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
