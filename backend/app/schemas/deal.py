"""Pydantic schemas for deals."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.deal import ItemCategory
from app.models.merchant import TierLevel


class DealItemBase(BaseModel):
    category: ItemCategory = ItemCategory.MAIN
    item_name: str = Field(..., max_length=255)
    individual_price: Decimal = Field(..., ge=0)


class DealItemCreate(DealItemBase):
    pass


class DealItemRead(DealItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_id: UUID


class DealTranslationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language_code: str
    title: str
    description: str


class DealBase(BaseModel):
    scraped_raw_url: Optional[str] = None
    clean_url: Optional[str] = None
    affiliate_url: Optional[str] = None
    original_price: Decimal = Field(..., ge=0)
    deal_price: Decimal = Field(..., ge=0)
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True
    tier_priority_score: int = 0
    slot_exempt: bool = False
    image_url: Optional[str] = None
    venue_category: Optional[str] = Field(default=None, max_length=120)
    expires_at: Optional[datetime] = None


class DealCreate(DealBase):
    merchant_id: UUID
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    language_code: str = Field(default="en", min_length=2, max_length=5)
    items: List[DealItemCreate] = Field(default_factory=list)


class DealUpdate(BaseModel):
    is_active: Optional[bool] = None
    deal_price: Optional[Decimal] = Field(default=None, ge=0)
    original_price: Optional[Decimal] = Field(default=None, ge=0)
    currency_code: Optional[str] = Field(default=None, min_length=3, max_length=3)
    image_url: Optional[str] = None
    venue_category: Optional[str] = Field(default=None, max_length=120)
    expires_at: Optional[datetime] = None
    tier_priority_score: Optional[int] = None
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    language_code: Optional[str] = Field(default=None, min_length=2, max_length=5)
    items: Optional[List[DealItemCreate]] = None
    # Soft-delete: hide from merchant profile + public feed; keep DB row for analytics.
    remove_from_profile: Optional[bool] = None


class DealRead(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    reposted_from_id: Optional[UUID] = None
    created_at: datetime
    items: List[DealItemRead] = Field(default_factory=list)
    translations: List[DealTranslationRead] = Field(default_factory=list)


class DealDetailRead(DealRead):
    """Deal detail with merchant / location context for public pages."""

    merchant_name: str
    logo_url: Optional[str] = None
    # Scraped business about blurb (merchant.bio)
    about_blurb: Optional[str] = None
    tier_level: TierLevel = TierLevel.FREE
    is_subscriber: bool = False
    city: Optional[str] = None
    area_local: Optional[str] = None
    country_code: Optional[str] = None


class DealFeedItem(BaseModel):
    """Deal as returned in the geo-ranked feed."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    merchant_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    original_price: Decimal
    deal_price: Decimal
    currency_code: str
    converted_deal_price: Optional[Decimal] = None
    converted_currency: Optional[str] = None
    distance_km: Optional[float] = None
    feed_score: float
    affiliate_url: Optional[str] = None
    clean_url: Optional[str] = None
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    venue_category: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    city: Optional[str] = None
    area_local: Optional[str] = None
    country_code: Optional[str] = None
    tier_level: TierLevel = TierLevel.FREE
    is_subscriber: bool = False


class DealFeedResponse(BaseModel):
    count: int
    results: List[DealFeedItem]


class ValueCalculatorResponse(BaseModel):
    deal_id: UUID
    deal_price: Decimal
    items_total: Decimal
    savings_amount: Decimal
    savings_percent: float
    currency_code: str
    items: List[DealItemRead]
