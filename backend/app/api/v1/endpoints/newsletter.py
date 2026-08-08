"""Newsletter subscribe / soft-unsubscribe / resubscribe APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import DbSession
from app.models.newsletter import NewsletterSubscriber
from app.schemas.newsletter import (
    NewsletterActionResponse,
    NewsletterResubscribeRequest,
    NewsletterStatusResponse,
    NewsletterSubscribeRequest,
    NewsletterSubscriberRead,
    NewsletterUnsubscribeEmailRequest,
)
from app.services.newsletter import (
    new_unsubscribe_token,
    normalize_email,
    soft_resubscribe,
    soft_unsubscribe,
)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.post(
    "/subscribe",
    response_model=NewsletterSubscriberRead,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    payload: NewsletterSubscribeRequest,
    db: DbSession,
) -> NewsletterSubscriber:
    email = normalize_email(str(payload.email))
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        # Re-activate + refresh capture fields; never delete history
        existing.name = payload.name.strip()
        existing.surname = payload.surname.strip()
        existing.location = payload.location.strip()
        if payload.country_code:
            existing.country_code = payload.country_code.strip().lower()
        if payload.city:
            existing.city = payload.city.strip()
        soft_resubscribe(existing)
        await db.flush()
        await db.refresh(existing)
        return existing

    subscriber = NewsletterSubscriber(
        name=payload.name.strip(),
        surname=payload.surname.strip(),
        email=email,
        location=payload.location.strip(),
        country_code=(
            payload.country_code.strip().lower() if payload.country_code else None
        ),
        city=payload.city.strip() if payload.city else None,
        is_subscribed=True,
        unsubscribe_token=new_unsubscribe_token(),
    )
    db.add(subscriber)
    await db.flush()
    await db.refresh(subscriber)
    return subscriber


@router.post("/unsubscribe", response_model=NewsletterActionResponse)
async def unsubscribe_by_token(
    db: DbSession,
    token: str = Query(..., min_length=8),
) -> NewsletterActionResponse:
    result = await db.execute(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.unsubscribe_token == token
        )
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found",
        )
    soft_unsubscribe(subscriber)
    await db.flush()
    return NewsletterActionResponse(
        message="You've been unsubscribed. Your details stay on file.",
        email=subscriber.email,
        is_subscribed=False,
    )


@router.post("/unsubscribe-email", response_model=NewsletterActionResponse)
async def unsubscribe_by_email(
    payload: NewsletterUnsubscribeEmailRequest,
    db: DbSession,
) -> NewsletterActionResponse:
    """Soft-unsubscribe using the email stored on this device (newsletter portal)."""
    email = normalize_email(str(payload.email))
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No newsletter record for that email.",
        )
    soft_unsubscribe(subscriber)
    await db.flush()
    return NewsletterActionResponse(
        message="You've been unsubscribed. Your details stay on file.",
        email=subscriber.email,
        is_subscribed=False,
    )


@router.post("/resubscribe", response_model=NewsletterActionResponse)
async def resubscribe(
    payload: NewsletterResubscribeRequest,
    db: DbSession,
) -> NewsletterActionResponse:
    email = normalize_email(str(payload.email))
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No newsletter record for that email. Use subscribe instead.",
        )
    if payload.token and payload.token != subscriber.unsubscribe_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid resubscribe token",
        )
    soft_resubscribe(subscriber)
    await db.flush()
    return NewsletterActionResponse(
        message="Welcome back — you'll get weekly specials every Friday.",
        email=subscriber.email,
        is_subscribed=True,
    )


@router.get("/status", response_model=NewsletterStatusResponse)
async def subscription_status(
    db: DbSession,
    email: str = Query(..., min_length=3),
) -> NewsletterStatusResponse:
    normalized = normalize_email(email)
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == normalized)
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        return NewsletterStatusResponse(
            email=normalized, is_subscribed=False, exists=False
        )
    return NewsletterStatusResponse(
        email=subscriber.email,
        is_subscribed=subscriber.is_subscribed,
        exists=True,
    )
