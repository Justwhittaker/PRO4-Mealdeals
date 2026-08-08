"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    contact,
    currency,
    deals,
    design_requests,
    geo,
    marketing,
    merchants,
    newsletter,
    redirect,
    scrapers,
)

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(deals.router)
api_router.include_router(merchants.router)
api_router.include_router(geo.router)
api_router.include_router(scrapers.router)
api_router.include_router(design_requests.router)
api_router.include_router(newsletter.router)
api_router.include_router(contact.router)
api_router.include_router(currency.router)
api_router.include_router(marketing.router)
# /go/{deal_id} is mounted at app root as well; keep under v1 for discoverability
api_router.include_router(redirect.router)
