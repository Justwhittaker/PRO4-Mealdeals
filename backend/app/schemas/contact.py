"""Schemas for the public contact form."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactMessageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    surname: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=3, max_length=60)
    business: Optional[str] = Field(default=None, max_length=255)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)


class ContactMessageResponse(BaseModel):
    message: str
    delivered: bool
