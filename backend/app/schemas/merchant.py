"""Pydantic schemas for merchant profiles."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.merchant import MerchantCategory, TierLevel
from app.schemas.deal import DealRead


class LocationBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    country_code: str
    city: str
    timezone: str
    latitude: float
    longitude: float


class MerchantBase(BaseModel):
    name: str = Field(..., max_length=255)
    category: MerchantCategory = MerchantCategory.RETAIL
    is_subscriber: bool = False
    tier_level: TierLevel = TierLevel.FREE
    deal_slot_limit: int = 0
    subscription_phase: str = "none"
    email: Optional[str] = Field(default=None, max_length=255)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255)


class MerchantCreate(MerchantBase):
    location_id: UUID


class MerchantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    category: Optional[MerchantCategory] = None
    location_id: Optional[UUID] = None
    is_subscriber: Optional[bool] = None
    tier_level: Optional[TierLevel] = None
    deal_slot_limit: Optional[int] = Field(default=None, ge=0, le=3)
    subscription_phase: Optional[str] = None
    email: Optional[str] = Field(default=None, max_length=255)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = None
    logo_url: Optional[str] = Field(default=None, max_length=500)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255)


class MerchantRead(MerchantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    location: Optional[LocationBrief] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MerchantProfile(MerchantRead):
    """Profile view with slot usage for the dashboard."""

    active_deal_count: int = 0
    total_deal_count: int = 0
    open_slots: int = 0
    used_free_trial: bool = False


class TrialEligibilityResponse(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    contact_path: str = "/contact"


class TrialClaimResponse(BaseModel):
    claimed: bool
    message: str


class MerchantListResponse(BaseModel):
    count: int
    results: List[MerchantRead]


class MerchantDealHistoryResponse(BaseModel):
    merchant_id: UUID
    count: int
    active_count: int
    open_slots: int
    results: List[DealRead]


class RepostDealResponse(BaseModel):
    deal: DealRead
    message: str
