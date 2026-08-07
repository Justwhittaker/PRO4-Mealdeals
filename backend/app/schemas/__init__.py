"""Pydantic schema package."""

from __future__ import annotations

from app.schemas.deal import (
    DealCreate,
    DealFeedItem,
    DealFeedResponse,
    DealItemCreate,
    DealItemRead,
    DealRead,
    ValueCalculatorResponse,
)
from app.schemas.merchant import (
    MerchantCreate,
    MerchantListResponse,
    MerchantRead,
    MerchantUpdate,
)

__all__ = [
    "DealCreate",
    "DealFeedItem",
    "DealFeedResponse",
    "DealItemCreate",
    "DealItemRead",
    "DealRead",
    "MerchantCreate",
    "MerchantListResponse",
    "MerchantRead",
    "MerchantUpdate",
    "ValueCalculatorResponse",
]
