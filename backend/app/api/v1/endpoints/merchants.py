"""Merchant profile, subscription state, deal history, and repost."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.models.deal import Deal, DealItem
from app.models.location import Location
from app.models.merchant import PAID_DEAL_SLOT_LIMIT, Merchant, TierLevel
from app.models.translation import DealTranslation
from app.schemas.deal import DealRead
from app.schemas.merchant import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MerchantCreate,
    MerchantDealHistoryResponse,
    MerchantListResponse,
    MerchantProfile,
    MerchantRead,
    MerchantUpdate,
    RepostDealResponse,
    TrialClaimResponse,
    TrialEligibilityResponse,
)
from app.services.email import send_email
from app.services.trial import check_trial_eligibility, record_trial_claim

router = APIRouter(prefix="/merchants", tags=["merchants"])


async def _active_deal_count(db: DbSession, merchant_id: UUID) -> int:
    """Count Priority-slot deals only (designed specials are slot_exempt)."""
    return (
        await db.execute(
            select(func.count())
            .select_from(Deal)
            .where(
                Deal.merchant_id == merchant_id,
                Deal.is_active.is_(True),
                Deal.slot_exempt.is_(False),
            )
        )
    ).scalar_one()


async def _total_deal_count(db: DbSession, merchant_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Deal)
            .where(Deal.merchant_id == merchant_id)
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
        used_free_trial=bool(merchant.used_free_trial),
    )


@router.get("", response_model=MerchantListResponse)
async def list_merchants(
    db: DbSession,
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
    city: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> MerchantListResponse:
    stmt = select(Merchant)
    count_stmt = select(func.count()).select_from(Merchant)

    if country_code or city:
        stmt = stmt.join(Location, Merchant.location_id == Location.id)
        count_stmt = count_stmt.join(Location, Merchant.location_id == Location.id)
        if country_code:
            code = country_code.upper()
            if code == "UK":
                code = "GB"
            stmt = stmt.where(Location.country_code == code)
            count_stmt = count_stmt.where(Location.country_code == code)
        if city:
            stmt = stmt.where(func.lower(Location.city) == city.lower())
            count_stmt = count_stmt.where(func.lower(Location.city) == city.lower())

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt.offset(skip).limit(limit).order_by(Merchant.name))
    merchants = list(result.scalars().unique().all())
    return MerchantListResponse(count=total, results=merchants)


@router.post("", response_model=MerchantRead, status_code=status.HTTP_201_CREATED)
async def create_merchant(payload: MerchantCreate, db: DbSession) -> Merchant:
    location = await db.get(Location, payload.location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="location_id does not exist",
        )
    if payload.email:
        existing = await db.execute(
            select(Merchant).where(Merchant.email == str(payload.email).lower())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A profile with this email already exists",
            )

    merchant = Merchant(
        name=payload.name,
        category=payload.category,
        location_id=payload.location_id,
        is_subscriber=payload.is_subscriber,
        tier_level=payload.tier_level,
        deal_slot_limit=payload.deal_slot_limit,
        subscription_phase=payload.subscription_phase,
        email=str(payload.email).lower() if payload.email else None,
        contact_name=payload.contact_name,
        phone=payload.phone,
        website=payload.website,
        bio=payload.bio,
        logo_url=payload.logo_url,
        stripe_customer_id=payload.stripe_customer_id,
    )
    _sync_subscription_fields(merchant)
    db.add(merchant)
    await db.flush()
    await db.refresh(merchant)
    return merchant


@router.get("/by-email/{email}", response_model=MerchantProfile)
async def get_profile_by_email(email: str, db: DbSession) -> MerchantProfile:
    result = await db.execute(
        select(Merchant).where(Merchant.email == email.lower())
    )
    merchant = result.scalar_one_or_none()
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await _profile_from_merchant(db, merchant)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: DbSession,
) -> ForgotPasswordResponse:
    """Email sign-in reset instructions (does not reveal whether the account exists)."""
    email = str(payload.email).strip().lower()
    settings = get_settings()
    sign_in_url = f"{settings.frontend_base_url.rstrip('/')}/dashboard"

    result = await db.execute(select(Merchant).where(Merchant.email == email))
    merchant = result.scalar_one_or_none()
    if merchant is not None:
        subject = "Reset your Dine A Deal merchant sign-in"
        text_body = "\n".join(
            [
                "You requested a password reset for your Dine A Deal merchant account.",
                "",
                f"Open Merchant Sign in: {sign_in_url}",
                "Enter this email and choose a new password, then sign in.",
                "If you use Google, click Continue with Google on that page instead.",
                "",
                "If you did not request this, you can ignore this email.",
            ]
        )
        send_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
        )

    return ForgotPasswordResponse(
        message=(
            "If an account exists for that email, reset instructions have been sent."
        ),
        email=email,
    )


@router.get("/{merchant_id}/profile", response_model=MerchantProfile)
async def get_profile(merchant_id: UUID, db: DbSession) -> MerchantProfile:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return await _profile_from_merchant(db, merchant)


@router.get(
    "/{merchant_id}/trial-eligibility",
    response_model=TrialEligibilityResponse,
)
async def trial_eligibility(
    merchant_id: UUID,
    db: DbSession,
) -> TrialEligibilityResponse:
    """Whether this merchant may start the free Priority month (anti-abuse)."""
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found"
        )
    result = await check_trial_eligibility(db, merchant)
    return TrialEligibilityResponse(
        eligible=result.eligible,
        reason=result.reason,
        contact_path=result.contact_path,
    )


@router.post(
    "/{merchant_id}/claim-trial",
    response_model=TrialClaimResponse,
)
async def claim_trial(
    merchant_id: UUID,
    db: DbSession,
) -> TrialClaimResponse:
    """
    Record free-month claim (email / business / location).

    Called from Stripe webhook after successful trial checkout.
    """
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found"
        )
    try:
        await record_trial_claim(db, merchant)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return TrialClaimResponse(
        claimed=True,
        message="Free month claimed. Card on file will be charged after the trial.",
    )


@router.patch("/{merchant_id}/profile", response_model=MerchantProfile)
async def update_profile(
    merchant_id: UUID,
    payload: MerchantUpdate,
    db: DbSession,
) -> MerchantProfile:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = str(data["email"]).lower()
        clash = await db.execute(
            select(Merchant).where(
                Merchant.email == data["email"],
                Merchant.id != merchant_id,
            )
        )
        if clash.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A profile with this email already exists",
            )

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


@router.get("/{merchant_id}/deals/history", response_model=MerchantDealHistoryResponse)
async def deal_history(
    merchant_id: UUID,
    db: DbSession,
    include_inactive: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> MerchantDealHistoryResponse:
    """Full deal history for the merchant profile (active + past)."""
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    stmt = (
        select(Deal)
        .where(Deal.merchant_id == merchant_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
        .order_by(Deal.created_at.desc())
        .limit(limit)
    )
    if not include_inactive:
        stmt = stmt.where(Deal.is_active.is_(True))

    deals = list((await db.execute(stmt)).scalars().unique().all())
    active = await _active_deal_count(db, merchant_id)
    limit_slots = merchant.deal_slot_limit or 0

    return MerchantDealHistoryResponse(
        merchant_id=merchant_id,
        count=len(deals),
        active_count=active,
        open_slots=max(limit_slots - active, 0),
        results=deals,
    )


@router.post(
    "/{merchant_id}/deals/{deal_id}/repost",
    response_model=RepostDealResponse,
    status_code=status.HTTP_201_CREATED,
)
async def repost_deal(
    merchant_id: UUID,
    deal_id: UUID,
    db: DbSession,
) -> RepostDealResponse:
    """
    Clone a past deal into a new active Priority slot.

    Keeps the original in history and links via reposted_from_id.
    """
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")

    if not merchant.is_subscriber or (merchant.deal_slot_limit or 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Reposting requires an active Priority subscription (3 slots).",
        )

    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id, Deal.merchant_id == merchant_id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    active = await _active_deal_count(db, merchant_id)
    if active >= merchant.deal_slot_limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"No open slots ({active}/{merchant.deal_slot_limit}). "
                "Deactivate a live deal before reposting."
            ),
        )

    clone = Deal(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        reposted_from_id=source.id,
        scraped_raw_url=source.scraped_raw_url,
        clean_url=source.clean_url,
        affiliate_url=source.affiliate_url,
        original_price=source.original_price,
        deal_price=source.deal_price,
        currency_code=source.currency_code,
        is_active=True,
        tier_priority_score=max(source.tier_priority_score, 200),
        expires_at=None,
    )
    db.add(clone)
    await db.flush()

    for item in source.items:
        db.add(
            DealItem(
                id=uuid.uuid4(),
                deal_id=clone.id,
                category=item.category,
                item_name=item.item_name,
                individual_price=item.individual_price,
            )
        )

    for translation in source.translations:
        db.add(
            DealTranslation(
                id=uuid.uuid4(),
                deal_id=clone.id,
                language_code=translation.language_code,
                title=translation.title,
                description=translation.description,
            )
        )

    await db.flush()
    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == clone.id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    deal = loaded.scalar_one()

    return RepostDealResponse(
        deal=DealRead.model_validate(deal),
        message="Deal reposted into an open Priority slot. Original kept in history.",
    )


@router.get("/{merchant_id}", response_model=MerchantRead)
async def get_merchant(merchant_id: UUID, db: DbSession) -> Merchant:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return merchant


@router.patch("/{merchant_id}", response_model=MerchantRead)
async def update_merchant(
    merchant_id: UUID,
    payload: MerchantUpdate,
    db: DbSession,
) -> Merchant:
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
    return merchant


@router.delete(
    "/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_merchant(merchant_id: UUID, db: DbSession) -> None:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    await db.delete(merchant)
    await db.flush()
    return None
