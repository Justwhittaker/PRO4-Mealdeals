"""Deal design requests — €20 one-time, slot-exempt, 2-month live deals."""

from __future__ import annotations

import html
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession
from app.core.config import get_settings
from app.models.deal import Deal, DealItem, ItemCategory
from app.models.design_request import DesignRequest, DesignRequestStatus
from app.models.merchant import Merchant
from app.models.translation import DealTranslation
from app.schemas.deal import DealRead
from app.schemas.design_request import (
    DesignFulfillPayload,
    DesignFulfillResponse,
    DesignInboundEmailPayload,
    DesignMarkPaidPayload,
    DesignRequestCreate,
    DesignRequestListResponse,
    DesignRequestRead,
    DesignRequestUpdate,
)
from app.services.email import is_email_configured, send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/design-requests", tags=["design-requests"])

DESIGN_DURATION_DAYS = 60
_REQUEST_ID_RE = re.compile(
    r"DESIGN[:\s#-]*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
    re.IGNORECASE,
)


async def _get_request(db: DbSession, request_id: UUID) -> DesignRequest:
    row = await db.get(DesignRequest, request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return row


@router.post("", response_model=DesignRequestRead, status_code=status.HTTP_201_CREATED)
async def create_design_request(
    payload: DesignRequestCreate, db: DbSession
) -> DesignRequest:
    merchant = await db.get(Merchant, payload.merchant_id)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="merchant_id does not exist"
        )

    req = DesignRequest(
        id=uuid.uuid4(),
        merchant_id=payload.merchant_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        details=payload.details.strip(),
        photo_urls=list(payload.photo_urls or []),
        status=DesignRequestStatus.PENDING_PAYMENT,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


@router.get("", response_model=DesignRequestListResponse)
async def list_design_requests(
    db: DbSession,
    merchant_id: UUID | None = Query(default=None),
    status_filter: DesignRequestStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> DesignRequestListResponse:
    stmt = select(DesignRequest).order_by(DesignRequest.created_at.desc()).limit(limit)
    count_stmt = select(func.count()).select_from(DesignRequest)
    if merchant_id:
        stmt = stmt.where(DesignRequest.merchant_id == merchant_id)
        count_stmt = count_stmt.where(DesignRequest.merchant_id == merchant_id)
    if status_filter:
        stmt = stmt.where(DesignRequest.status == status_filter)
        count_stmt = count_stmt.where(DesignRequest.status == status_filter)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = list((await db.execute(stmt)).scalars().all())
    return DesignRequestListResponse(count=total, results=rows)


@router.get("/{request_id}", response_model=DesignRequestRead)
async def get_design_request(request_id: UUID, db: DbSession) -> DesignRequest:
    return await _get_request(db, request_id)


@router.patch("/{request_id}", response_model=DesignRequestRead)
async def update_design_request(
    request_id: UUID, payload: DesignRequestUpdate, db: DbSession
) -> DesignRequest:
    req = await _get_request(db, request_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(req, field, value)
    if req.status == DesignRequestStatus.PAID and req.paid_at is None:
        req.paid_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(req)
    return req


@router.post(
    "/{request_id}/mark-paid",
    response_model=DesignRequestRead,
)
async def mark_design_request_paid(
    request_id: UUID,
    payload: DesignMarkPaidPayload,
    db: DbSession,
) -> DesignRequest:
    """Called from the Stripe webhook after €20 Checkout completes."""
    req = await _get_request(db, request_id)
    already_paid = req.status == DesignRequestStatus.PAID and req.paid_at is not None
    req.status = DesignRequestStatus.PAID
    req.paid_at = req.paid_at or datetime.now(timezone.utc)
    if payload.stripe_checkout_session_id:
        req.stripe_checkout_session_id = payload.stripe_checkout_session_id
    if payload.stripe_payment_intent_id:
        req.stripe_payment_intent_id = payload.stripe_payment_intent_id
    await db.flush()
    await db.refresh(req)

    # Notify ops once when payment first lands (skip duplicate webhook retries).
    if not already_paid:
        _notify_ops_design_paid(req)

    return req


def _notify_ops_design_paid(req: DesignRequest) -> None:
    """Email the Design Deals ops inbox with brief + full DESIGN:{uuid} subject tag."""
    settings = get_settings()
    to_email = (settings.contact_to_email or "").strip() or "just.whittaker@gmail.com"
    if not is_email_configured(settings):
        logger.warning(
            "Design payment email skipped — email not configured. request=%s to=%s",
            req.id,
            to_email,
        )
        return

    merchant = req.merchant
    merchant_label = ""
    if merchant is not None:
        parts = [
            p
            for p in [merchant.name, merchant.email, merchant.contact_name]
            if p
        ]
        merchant_label = " · ".join(str(p) for p in parts)

    photos = list(req.photo_urls or [])
    photo_lines = "\n".join(f"- {url}" for url in photos) if photos else "(none)"
    design_tag = f"DESIGN:{req.id}"
    fulfill_url = (
        f"{settings.frontend_base_url.rstrip('/')}/dashboard/design/fulfill"
        f"?request={req.id}"
    )

    subject = f"Design Deals 4 U — payment received ({req.title[:80]})"
    text_body = "\n".join(
        [
            "A merchant paid for Design Deals 4 U.",
            "",
            f"Subject tag for inbound creative: {design_tag}",
            f"Manual fulfill: {fulfill_url}",
            "",
            f"Title: {req.title}",
            f"Merchant: {merchant_label or req.merchant_id}",
            f"Description: {req.description}",
            f"Brief: {req.details}",
            "",
            "Photo URLs:",
            photo_lines,
            "",
            f"Stripe session: {req.stripe_checkout_session_id or '(n/a)'}",
        ]
    )
    safe_title = html.escape(req.title)
    safe_merchant = html.escape(merchant_label or str(req.merchant_id))
    safe_desc = html.escape(req.description or "").replace("\n", "<br/>")
    safe_details = html.escape(req.details or "").replace("\n", "<br/>")
    safe_photos = (
        "<br/>".join(html.escape(url) for url in photos) if photos else "(none)"
    )
    html_body = f"""
    <p><strong>A merchant paid for Design Deals 4 U.</strong></p>
    <p>Inbound creative subject must include:<br/>
    <code>{html.escape(design_tag)}</code></p>
    <p><a href="{html.escape(fulfill_url)}">Open manual fulfill</a></p>
    <p><strong>Title:</strong> {safe_title}<br/>
    <strong>Merchant:</strong> {safe_merchant}</p>
    <p><strong>Description</strong><br/>{safe_desc}</p>
    <p><strong>Brief</strong><br/>{safe_details}</p>
    <p><strong>Photos</strong><br/>{safe_photos}</p>
    """

    delivered = send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    if delivered:
        logger.info("Design payment ops email sent request=%s to=%s", req.id, to_email)
    else:
        logger.error(
            "Design payment ops email failed request=%s to=%s", req.id, to_email
        )


async def _fulfill(
    db: DbSession,
    req: DesignRequest,
    *,
    image_url: str,
    title: str | None,
    description: str | None,
    deal_price: Decimal,
    original_price: Decimal,
    currency_code: str,
) -> tuple[DesignRequest, Deal]:
    if req.status not in (
        DesignRequestStatus.PAID,
        DesignRequestStatus.IN_DESIGN,
        DesignRequestStatus.POSTED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must be paid before fulfillment",
        )

    if req.deal_id and req.status == DesignRequestStatus.POSTED:
        existing = await db.get(Deal, req.deal_id)
        if existing:
            return req, existing

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=DESIGN_DURATION_DAYS)
    deal_title = (title or req.title).strip()
    deal_desc = (description or req.description or req.details).strip()

    deal = Deal(
        id=uuid.uuid4(),
        merchant_id=req.merchant_id,
        scraped_raw_url=None,
        clean_url=None,
        affiliate_url=None,
        original_price=original_price,
        deal_price=deal_price,
        currency_code=currency_code.upper(),
        is_active=True,
        tier_priority_score=300,
        slot_exempt=True,
        image_url=image_url,
        expires_at=expires,
        created_at=now,
    )
    db.add(deal)
    await db.flush()

    db.add(
        DealItem(
            id=uuid.uuid4(),
            deal_id=deal.id,
            category=ItemCategory.MAIN,
            item_name=deal_title[:255],
            individual_price=original_price or deal_price,
        )
    )
    db.add(
        DealTranslation(
            id=uuid.uuid4(),
            deal_id=deal.id,
            language_code="en",
            title=deal_title[:255],
            description=deal_desc,
        )
    )

    req.status = DesignRequestStatus.POSTED
    req.posted_at = now
    req.deal_id = deal.id
    req.fulfillment_image_url = image_url
    await db.flush()

    loaded = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.items), selectinload(Deal.translations))
    )
    return req, loaded.scalar_one()


@router.post(
    "/{request_id}/fulfill",
    response_model=DesignFulfillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fulfill_design_request(
    request_id: UUID,
    payload: DesignFulfillPayload,
    db: DbSession,
    x_design_fulfill_secret: str | None = Header(default=None),
) -> DesignFulfillResponse:
    """
    Post the designed creative as a slot-exempt deal lasting 2 months.

    Protect with DESIGN_FULFILL_SECRET header in production.
    """
    settings = get_settings()
    expected = getattr(settings, "design_fulfill_secret", None) or ""
    if expected and x_design_fulfill_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")

    req = await _get_request(db, request_id)
    if req.status == DesignRequestStatus.PENDING_PAYMENT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment required before fulfillment",
        )

    req.status = DesignRequestStatus.IN_DESIGN
    await db.flush()

    req, deal = await _fulfill(
        db,
        req,
        image_url=payload.image_url,
        title=payload.title,
        description=payload.description,
        deal_price=Decimal(str(payload.deal_price)),
        original_price=Decimal(str(payload.original_price)),
        currency_code=payload.currency_code,
    )

    return DesignFulfillResponse(
        request=DesignRequestRead.model_validate(req),
        deal=DealRead.model_validate(deal),
        message=(
            "Designed deal posted for 60 days. "
            "It does not use a Priority subscription slot."
        ),
    )


@router.post(
    "/inbound-email",
    response_model=DesignFulfillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fulfill_from_inbound_email(
    payload: DesignInboundEmailPayload,
    db: DbSession,
) -> DesignFulfillResponse:
    """
    Auto-post when you email an attachment.

    Subject must contain DESIGN:{uuid}. Body/attachment_url is the creative.
    Set DESIGN_FULFILL_SECRET and pass it as payload.secret.
    """
    settings = get_settings()
    expected = getattr(settings, "design_fulfill_secret", None) or "mealdeals-design"
    if payload.secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")

    match = _REQUEST_ID_RE.search(payload.subject)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject must include DESIGN:{request-uuid}",
        )
    request_id = UUID(match.group(1))
    req = await _get_request(db, request_id)

    if req.status == DesignRequestStatus.PENDING_PAYMENT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Request is not paid yet",
        )

    req.status = DesignRequestStatus.IN_DESIGN
    await db.flush()

    req, deal = await _fulfill(
        db,
        req,
        image_url=str(payload.attachment_url),
        title=req.title,
        description=payload.body_text or req.description,
        deal_price=Decimal("0"),
        original_price=Decimal("0"),
        currency_code="EUR",
    )

    logger.info("Inbound email fulfilled design request %s → deal %s", request_id, deal.id)
    return DesignFulfillResponse(
        request=DesignRequestRead.model_validate(req),
        deal=DealRead.model_validate(deal),
        message="Attachment posted automatically as a 2-month designed special.",
    )
