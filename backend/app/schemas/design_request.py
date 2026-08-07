"""Schemas for €20 deal-design requests."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.design_request import DesignRequestStatus
from app.schemas.deal import DealRead


class DesignRequestCreate(BaseModel):
    merchant_id: UUID
    title: str = Field(..., max_length=255)
    description: str = Field(default="", max_length=4000)
    details: str = Field(default="", max_length=8000)
    photo_urls: List[str] = Field(default_factory=list, max_length=8)


class DesignRequestUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    details: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    status: Optional[DesignRequestStatus] = None
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    notes: Optional[str] = None


class DesignRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    title: str
    description: str
    details: str
    photo_urls: List[str]
    status: DesignRequestStatus
    stripe_checkout_session_id: Optional[str] = None
    deal_id: Optional[UUID] = None
    fulfillment_image_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None


class DesignRequestListResponse(BaseModel):
    count: int
    results: List[DesignRequestRead]


class DesignFulfillPayload(BaseModel):
    """Ops fulfills a paid request — posts a slot-exempt 2-month deal."""

    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    image_url: str = Field(..., max_length=500)
    deal_price: float = Field(default=0, ge=0)
    original_price: float = Field(default=0, ge=0)
    currency_code: str = Field(default="EUR", min_length=3, max_length=3)
    notify_email: Optional[str] = None


class DesignFulfillResponse(BaseModel):
    request: DesignRequestRead
    deal: DealRead
    message: str


class DesignInboundEmailPayload(BaseModel):
    """
    Inbound email webhook body.

    Subject should include DESIGN:{request_uuid}
    Attachment hosted URL (or provider CDN link) in attachment_url.
    """

    subject: str
    attachment_url: HttpUrl | str
    body_text: Optional[str] = None
    secret: str


class DesignMarkPaidPayload(BaseModel):
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
