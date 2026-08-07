"""Free-month trial eligibility (one per email / business / location)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant
from app.models.trial_claim import TrialClaim

CONTACT_HINT = (
    "This free month has already been used for this email, business name, "
    "or venue location. Contact us if you believe this is a mistake."
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_business_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class TrialEligibility:
    eligible: bool
    reason: str | None = None
    contact_path: str = "/contact"
    email_normalized: str | None = None
    business_name_normalized: str | None = None
    location_id: UUID | None = None


async def check_trial_eligibility(
    db: AsyncSession,
    merchant: Merchant,
) -> TrialEligibility:
    if merchant.used_free_trial:
        return TrialEligibility(eligible=False, reason=CONTACT_HINT)

    email = merchant.email
    if not email:
        return TrialEligibility(
            eligible=False,
            reason="Add a business email on your profile before starting a free month.",
        )

    email_n = normalize_email(email)
    name_n = normalize_business_name(merchant.name)
    location_id = merchant.location_id

    result = await db.execute(
        select(TrialClaim).where(
            or_(
                TrialClaim.email_normalized == email_n,
                TrialClaim.business_name_normalized == name_n,
                TrialClaim.location_id == location_id,
            )
        )
    )
    existing = result.scalars().first()
    if existing is not None:
        return TrialEligibility(eligible=False, reason=CONTACT_HINT)

    # Also block if another merchant at same location / name already subscribed via trial
    other = await db.execute(
        select(Merchant).where(
            Merchant.id != merchant.id,
            Merchant.used_free_trial.is_(True),
            or_(
                Merchant.email == email_n,
                Merchant.location_id == location_id,
            ),
        )
    )
    if other.scalars().first() is not None:
        return TrialEligibility(eligible=False, reason=CONTACT_HINT)

    return TrialEligibility(
        eligible=True,
        email_normalized=email_n,
        business_name_normalized=name_n,
        location_id=location_id,
    )


async def record_trial_claim(
    db: AsyncSession,
    merchant: Merchant,
) -> TrialClaim:
    eligibility = await check_trial_eligibility(db, merchant)
    if not eligibility.eligible:
        # Idempotent: if this merchant already claimed, return existing
        if merchant.used_free_trial and merchant.email:
            result = await db.execute(
                select(TrialClaim).where(
                    TrialClaim.email_normalized
                    == normalize_email(merchant.email)
                )
            )
            claim = result.scalar_one_or_none()
            if claim:
                return claim
        raise ValueError(eligibility.reason or CONTACT_HINT)

    assert eligibility.email_normalized
    assert eligibility.business_name_normalized
    assert eligibility.location_id

    claim = TrialClaim(
        merchant_id=merchant.id,
        email_normalized=eligibility.email_normalized,
        business_name_normalized=eligibility.business_name_normalized,
        location_id=eligibility.location_id,
    )
    merchant.used_free_trial = True
    if merchant.subscription_phase in {"none", ""}:
        merchant.subscription_phase = "trial"
    db.add(claim)
    await db.flush()
    return claim
