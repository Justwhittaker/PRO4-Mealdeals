"""Pydantic schemas for newsletter subscribe / soft unsubscribe."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class NewsletterSubscribeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    surname: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    location: str = Field(..., min_length=1, max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=8)
    city: Optional[str] = Field(default=None, max_length=120)


class NewsletterResubscribeRequest(BaseModel):
    email: EmailStr
    # Optional: if provided, must match stored token
    token: Optional[str] = None


class NewsletterSubscriberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    surname: str = ""
    email: EmailStr
    location: str
    country_code: Optional[str] = None
    city: Optional[str] = None
    is_subscribed: bool
    unsubscribed_at: Optional[datetime] = None
    created_at: datetime


class NewsletterStatusResponse(BaseModel):
    email: EmailStr
    is_subscribed: bool
    exists: bool


class NewsletterActionResponse(BaseModel):
    message: str
    email: EmailStr
    is_subscribed: bool
