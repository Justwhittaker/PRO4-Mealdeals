"""Staff admin endpoints — merchants + deals CRUD behind X-Admin-Key."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminKey, DbSession
from app.models.deal import Deal, DealItem
from app.models.location import Location
from app.models.merchant import PAID_DEAL_SLOT_LIMIT, Merchant, TierLevel
from app.models.translation import DealTranslation
from app.schemas.deal import DealCreate, DealRead, DealUpdate
from app.schemas.merchant import (
    MerchantCreate,
    MerchantListResponse,
    MerchantProfile,
    MerchantRead,
    MerchantUpdate,
)
from app.services.affiliate import build_affiliate_urls
from app.services.deal_copy import clean_deal_description
from app.scrapers.categories import venue_category_id

router = APIRouter(prefix="/admin", tags=["admin"])


async def _active_deal_count(db: DbSession, merchant_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Deal)
            .where(
                Deal.merchant_id == merchant_id,
                Deal.is_active.is_(True),
                Deal.slot_exempt.is_(False),
                Deal.deleted_at.is_(None),
            )
        )
    ).scalar_one()


async def _total_deal_count(db: DbSession, merchant_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Deal)
            .where(
                Deal.merchant_id == merchant_id,
                Deal.deleted_at.is_(None),
            )
        )
    ).scalar_one()


def _sync_subscription_fields(merchant: Merchant) -> None:
    if merchant.is_subscriber and merchant.tier_level != TierLevel.FREE:
        if merchant.deal_slot_limit <= 0:
            merchant.deal_slot_limit = PAID_DEAL_SLOT_LIMIT
        if merchant.subscription_phase == "none":
            merchant.subscription_phase = "intro"
    elif not merchant.is_subscriber:
        merchant.deal_slot_limit = 0
        merchant.subscription_phase = "none"
        merchant.tier_level = TierLevel.FREE


async def _profile_from_merchant(db: DbSession, merchant: Merchant) -> MerchantProfile:
    active = await _active_deal_count(db, merchant.id)
    total = await _total_deal_count(db, merchant.id)
    limit = merchant.deal_slot_limit or 0
    return MerchantProfile(
        id=merchant.id,
        name=merchant.name,
        category=merchant.category,
        is_subscriber=merchant.is_subscriber,
        tier_level=merchant.tier_level,
        deal_slot_limit=merchant.deal_slot_limit,
        subscription_phase=merchant.subscription_phase,
        email=merchant.email,
        contact_name=merchant.contact_name,
        phone=merchant.phone,
        website=merchant.website,
        bio=merchant.bio,
        logo_url=merchant.logo_url,
        stripe_customer_id=merchant.stripe_customer_id,
        location_id=merchant.location_id,
        location=merchant.location,
        created_at=merchant.created_at,
        updated_at=merchant.updated_at,
        active_deal_count=active,
        total_deal_count=total,
        open_slots=max(limit - active, 0),
        used_free_trial=merchant.used_free_trial,
    )


@router.get("/health")
async def admin_health(_: AdminKey) -> dict[str, str]:
    return {"status": "ok", "scope": "admin"}


@router.get("/merchants", response_model=MerchantListResponse)
async def admin_list_merchants(
    _: AdminKey,
    db: DbSession,
    q: Optional[str] = Query(default=None, description="Search name or email"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> MerchantListResponse:
    stmt = select(Merchant).options(selectinload(Merchant.location))
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Merchant.name).like(term)
            | func.lower(func.coalesce(Merchant.email, "")).like(term)
        )
    stmt = stmt.order_by(Merchant.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return MerchantListResponse(
        count=len(rows),
        results=[MerchantRead.model_validate(m) for m in rows],
    )


@router.post(
    "/merchants",
    response_model=MerchantRead,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_merchant(
    _: AdminKey,
    payload: MerchantCreate,
    db: DbSession,
) -> Merchant:
    location = await db.get(Location, payload.location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="location_id does not exist",
        )
    data = payload.model_dump()
    if data.get("email"):
        data["email"] = str(data["email"]).lower()
    merchant = Merchant(id=uuid.uuid4(), **data)
    _sync_subscription_fields(merchant)
    db.add(merchant)
    await db.flush()
    await db.refresh(merchant)
    return merchant


@router.get("/merchants/{merchant_id}", response_model=MerchantProfile)
async def admin_get_merchant(
    merchant_id: UUID,
    _: AdminKey,
    db: DbSession,
) -> MerchantProfile:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return await _profile_from_merchant(db, merchant)


@router.patch("/merchants/{merchant_id}", response_model=MerchantProfile)
async def admin_update_merchant(
    merchant_id: UUID,
    payload: MerchantUpdate,
    _: AdminKey,
    db: DbSession,
) -> MerchantProfile:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = str(data["email"]).lower()
    if "location_id" in data:
        location = await db.get(Location, data["location_id"])
        if location is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="location_id does not exist",
            )

    for field, value in data.items():
        setattr(merchant, field, value)

    _sync_subscription_fields(merchant)
    await db.flush()
    await db.refresh(merchant)
    return await _profile_from_merchant(db, merchant)


@router.delete(
    "/merchants/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def admin_delete_merchant(
    merchant_id: UUID,
    _: AdminKey,
    db: DbSession,
) -> Response:
    """Remove merchant account and cascaded deals from the website."""
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    await db.delete(merchant)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/merchants/{merchant_id}/deals", response_model=List[DealRead])
async def admin_list_merchant_deals(
    merchant_id: UUID,
    _: AdminKey,
    db: DbSession,
    include_inactive: bool = Query(default=True),
) -> List[DealRead]:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    stmt = (
        select(Deal)
        .where(Deal.merchant_id == merchant_id)
        .where(Deal.deleted_at.is_(None))
        .options(selectinload(Deal.items), selectinload(Deal.translations))
        .order_by(Deal.created_at.desc())
    )
    if not include_inactive:
        stmt = stmt.where(Deal.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return [DealRead.model_validate(d) for d in rows]


@router.get("/deals", response_model=List[DealRead])
async def admin_list_deals(
    _: AdminKey,
    db: DbSession,
    merchant_id: Optional[UUID] = None,
    q: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> List[DealRead]:
    stmt = (
        select(Deal)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
        .order_by(Deal.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if merchant_id is not None:
        stmt = stmt.where(Deal.merchant_id == merchant_id)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = (
            stmt.join(Deal.translations)
            .where(func.lower(DealTranslation.title).like(term))
            .distinct()
        )
    rows = (await db.execute(stmt)).scalars().all()
    return [DealRead.model_validate(d) for d in rows]


@router.get("/deals/{deal_id}", response_model=DealRead)
async def admin_get_deal(
    deal_id: UUID,
    _: AdminKey,
    db: DbSession,
) -> DealRead:
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    deal = loaded.scalar_one_or_none()
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return DealRead.model_validate(deal)


@router.post(
    "/deals",
    response_model=DealRead,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_deal(
    payload: DealCreate,
    _: AdminKey,
    db: DbSession,
) -> DealRead:
    """Create a deal for any merchant — slot limits bypassed for staff."""
    merchant = await db.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merchant_id does not exist",
        )

    image_url = payload.image_url
    if image_url is not None:
        image_url = image_url.strip() or None

    clean_url = payload.clean_url
    affiliate_url = payload.affiliate_url
    if payload.scraped_raw_url and (not clean_url or not affiliate_url):
        generated_clean, generated_aff = build_affiliate_urls(payload.scraped_raw_url)
        clean_url = clean_url or generated_clean
        affiliate_url = affiliate_url or generated_aff

    resolved_category = None
    if payload.venue_category:
        resolved_category = venue_category_id(
            payload.venue_category, merchant_name=merchant.name
        )

    deal = Deal(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        scraped_raw_url=payload.scraped_raw_url,
        clean_url=clean_url,
        affiliate_url=affiliate_url,
        original_price=payload.original_price,
        deal_price=payload.deal_price,
        currency_code=payload.currency_code.upper(),
        is_active=payload.is_active,
        tier_priority_score=payload.tier_priority_score or 200,
        slot_exempt=True,  # staff-created deals never consume Priority slots
        image_url=image_url,
        venue_category=resolved_category or payload.venue_category,
        expires_at=payload.expires_at,
    )
    db.add(deal)
    await db.flush()

    title = (payload.title or merchant.name).strip() or merchant.name
    description = clean_deal_description(payload.description) or ""
    db.add(
        DealTranslation(
            id=uuid.uuid4(),
            deal_id=deal.id,
            language_code=payload.language_code or "en",
            title=title,
            description=description,
        )
    )

    for item in payload.items:
        db.add(
            DealItem(
                id=uuid.uuid4(),
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
    return DealRead.model_validate(loaded.scalar_one())


@router.patch("/deals/{deal_id}", response_model=DealRead)
async def admin_update_deal(
    deal_id: UUID,
    payload: DealUpdate,
    _: AdminKey,
    db: DbSession,
) -> DealRead:
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    deal = loaded.scalar_one_or_none()
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    data = payload.model_dump(exclude_unset=True)
    title = data.pop("title", None)
    description = data.pop("description", None)
    language_code = data.pop("language_code", None)
    items = data.pop("items", None)

    if "currency_code" in data and data["currency_code"]:
        data["currency_code"] = str(data["currency_code"]).upper()
    if "image_url" in data and data["image_url"] is not None:
        data["image_url"] = str(data["image_url"]).strip() or None
    if "venue_category" in data and data["venue_category"]:
        merchant = await db.get(Merchant, deal.merchant_id)
        data["venue_category"] = venue_category_id(
            data["venue_category"],
            merchant_name=merchant.name if merchant else None,
        )

    for field, value in data.items():
        setattr(deal, field, value)

    if title is not None or description is not None or language_code is not None:
        lang = language_code or "en"
        translation = next(
            (t for t in deal.translations if t.language_code == lang),
            None,
        )
        if translation is None:
            translation = DealTranslation(
                id=uuid.uuid4(),
                deal_id=deal.id,
                language_code=lang,
                title=title or "Deal",
                description=clean_deal_description(description) or "",
            )
            db.add(translation)
        else:
            if title is not None:
                translation.title = title
            if description is not None:
                translation.description = clean_deal_description(description) or ""

    if items is not None:
        for existing in list(deal.items):
            await db.delete(existing)
        await db.flush()
        for item in items:
            db.add(
                DealItem(
                    id=uuid.uuid4(),
                    deal_id=deal.id,
                    category=item.category,
                    item_name=item.item_name,
                    individual_price=item.individual_price
                    if isinstance(item.individual_price, Decimal)
                    else Decimal(str(item.individual_price)),
                )
            )

    await db.flush()
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    return DealRead.model_validate(loaded.scalar_one())


@router.delete(
    "/deals/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def admin_delete_deal(
    deal_id: UUID,
    _: AdminKey,
    db: DbSession,
) -> Response:
    deal = await db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    await db.delete(deal)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
