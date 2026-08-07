"""Marketing contact export (scraped hospitality business ledger)."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.dependencies import DbSession
from app.models.marketing_contact import MarketingContact

router = APIRouter(prefix="/marketing", tags=["marketing"])


class MarketingContactOut(BaseModel):
    id: str
    business_name: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    about_blurb: str | None = None
    country_code: str
    city: str | None = None


class MarketingContactsListResponse(BaseModel):
    count: int
    results: list[MarketingContactOut]


@router.get("/contacts", response_model=MarketingContactsListResponse)
async def list_marketing_contacts(
    db: DbSession,
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> MarketingContactsListResponse:
    """Browse scraped business contacts (name / phone / email)."""
    stmt = select(MarketingContact).order_by(
        MarketingContact.country_code.asc(),
        MarketingContact.business_name.asc(),
    )
    count_stmt = select(func.count()).select_from(MarketingContact)
    if country_code:
        code = country_code.upper()
        stmt = stmt.where(MarketingContact.country_code == code)
        count_stmt = count_stmt.where(MarketingContact.country_code == code)

    total = int((await db.execute(count_stmt)).scalar_one())
    rows = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return MarketingContactsListResponse(
        count=total,
        results=[
            MarketingContactOut(
                id=str(row.id),
                business_name=row.business_name,
                phone=row.phone,
                email=row.email,
                website=row.website,
                about_blurb=row.about_blurb,
                country_code=row.country_code,
                city=row.city,
            )
            for row in rows
        ],
    )


@router.get("/contacts/export")
async def export_marketing_contacts(
    db: DbSession,
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
) -> StreamingResponse:
    """CSV export of business_name, phone, email (+ website/about/geo)."""
    stmt = select(MarketingContact).order_by(
        MarketingContact.country_code.asc(),
        MarketingContact.business_name.asc(),
    )
    if country_code:
        stmt = stmt.where(MarketingContact.country_code == country_code.upper())
    rows = (await db.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "business_name",
            "phone",
            "email",
            "website",
            "about_blurb",
            "country_code",
            "city",
            "source_url",
            "last_scraped_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.business_name,
                row.phone or "",
                row.email or "",
                row.website or "",
                row.about_blurb or "",
                row.country_code,
                row.city or "",
                row.source_url or "",
                row.last_scraped_at.isoformat() if row.last_scraped_at else "",
            ]
        )
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="marketing_contacts.csv"'
        },
    )
