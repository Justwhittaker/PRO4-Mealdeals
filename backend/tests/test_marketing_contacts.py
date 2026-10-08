"""Marketing-contact upserts skip unchanged duplicates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.marketing_contact import MarketingContact
from app.services.marketing_contacts import upsert_marketing_contact


class _Result:
    def __init__(self, row: MarketingContact | None) -> None:
        self._row = row

    def scalar_one_or_none(self) -> MarketingContact | None:
        return self._row


class _Session:
    def __init__(
        self,
        *,
        by_email: MarketingContact | None = None,
        by_website: MarketingContact | None = None,
        by_name: MarketingContact | None = None,
    ) -> None:
        self.by_email = by_email
        self.by_website = by_website
        self.by_name = by_name
        self.added: list[MarketingContact] = []
        self.flushes = 0

    def execute(self, stmt: object) -> _Result:
        where = str(stmt).split("WHERE", 1)[-1]
        if "marketing_contacts.email =" in where:
            return _Result(self.by_email)
        if "marketing_contacts.website =" in where:
            return _Result(self.by_website)
        return _Result(self.by_name)

    def add(self, row: MarketingContact) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushes += 1


_SCRAPED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _contact(**overrides: object) -> MarketingContact:
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "business_name": "Cafe Nero",
        "website": "https://cafe.example",
        "phone": "+35311234567",
        "email": "hi@cafe.example",
        "about_blurb": "Coffee",
        "country_code": "IE",
        "city": "Dublin",
        "source_url": "https://cafe.example/menu",
        "venue_category": "cafe",
        "last_scraped_at": _SCRAPED,
        "created_at": _SCRAPED,
        "updated_at": _SCRAPED,
    }
    fields.update(overrides)
    return MarketingContact(**fields)


def _upsert(session: _Session, **overrides: object) -> MarketingContact | None:
    payload: dict[str, object] = {
        "business_name": "Cafe Nero",
        "website": "https://cafe.example",
        "phone": "+35311234567",
        "email": "hi@cafe.example",
        "about_blurb": "Coffee",
        "country_code": "IE",
        "city": "Dublin",
        "source_url": "https://cafe.example/menu",
        "venue_category": "cafe",
    }
    payload.update(overrides)
    return upsert_marketing_contact(session, **payload)  # type: ignore[arg-type]


def test_duplicate_with_no_new_data_is_not_written() -> None:
    existing = _contact()
    session = _Session(by_email=existing)

    result = _upsert(session)

    assert result is existing
    assert session.flushes == 0
    assert session.added == []
    assert existing.last_scraped_at == _SCRAPED
    assert existing.updated_at == _SCRAPED
    assert existing.email == "hi@cafe.example"


@pytest.mark.parametrize("stored_email", [None, "", "  "])
def test_duplicate_gaining_an_email_is_written(stored_email: str | None) -> None:
    existing = _contact(email=stored_email)
    session = _Session(by_website=existing)

    result = _upsert(session, email="owner@cafe.example")

    assert result is existing
    assert existing.email == "owner@cafe.example"
    assert session.flushes == 1
    assert session.added == []
    assert existing.last_scraped_at != _SCRAPED


def test_duplicate_keeps_a_stored_email() -> None:
    existing = _contact(email="hi@cafe.example")
    session = _Session(by_website=existing)

    result = _upsert(session, email="other@cafe.example")

    assert result is existing
    assert existing.email == "hi@cafe.example"
    assert session.flushes == 0
    assert existing.last_scraped_at == _SCRAPED


def test_duplicate_gains_a_missing_phone() -> None:
    existing = _contact(phone=None)
    session = _Session(by_email=existing)

    result = _upsert(session, phone="0851234567")

    assert result is existing
    assert existing.phone == "0851234567"
    assert session.flushes == 1
    assert existing.email == "hi@cafe.example"


def test_brand_new_contact_is_inserted() -> None:
    session = _Session()

    result = _upsert(session, email="owner@cafe.example")

    assert result is not None
    assert session.added == [result]
    assert session.flushes == 1
    assert result.email == "owner@cafe.example"
    assert result.business_name == "Cafe Nero"
    assert result.country_code == "IE"
    assert result.city == "Dublin"
    assert result.last_scraped_at is not None
