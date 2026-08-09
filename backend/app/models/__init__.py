"""ORM models package."""

from __future__ import annotations

from app.models.currency import Currency
from app.models.deal import Deal, DealItem, ItemCategory
from app.models.design_request import DesignRequest, DesignRequestStatus
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant, MerchantCategory, TierLevel
from app.models.newsletter import NewsletterSubscriber
from app.models.terms_acceptance import TermsAcceptance
from app.models.translation import DealTranslation
from app.models.trial_claim import TrialClaim

__all__ = [
    "Currency",
    "Deal",
    "DealItem",
    "DealTranslation",
    "DesignRequest",
    "DesignRequestStatus",
    "ItemCategory",
    "Location",
    "MarketingContact",
    "Merchant",
    "MerchantCategory",
    "NewsletterSubscriber",
    "TermsAcceptance",
    "TierLevel",
    "TrialClaim",
]
