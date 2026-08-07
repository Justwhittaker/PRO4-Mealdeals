"""Currency conversion helpers for geo-priced subscriptions."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.dependencies import CurrencySvc

router = APIRouter(prefix="/currency", tags=["currency"])


class ConvertResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted: float


@router.get("/convert", response_model=ConvertResponse)
async def convert_amount(
    currency_svc: CurrencySvc,
    amount: float = Query(..., gt=0),
    from_currency: str = Query(default="EUR", min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
) -> ConvertResponse:
    converted = await currency_svc.convert(
        Decimal(str(amount)),
        from_currency.upper(),
        to_currency.upper(),
    )
    if converted is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No FX rate for {from_currency} → {to_currency}",
        )
    return ConvertResponse(
        amount=amount,
        from_currency=from_currency.upper(),
        to_currency=to_currency.upper(),
        converted=float(converted),
    )
