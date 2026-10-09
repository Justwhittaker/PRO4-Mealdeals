#!/usr/bin/env python3
"""Render a Weekly Specials email without sending it.

From backend/:

  python scripts/preview_weekly_specials.py --city Galway --fixtures
  python scripts/preview_weekly_specials.py --city Galway --country IE --name Justin
  python scripts/preview_weekly_specials.py --location "Galway, Ireland" --fixtures

``--fixtures`` uses the built-in Galway issue sample (junk plus Irish
offers) and does not open the database. Without ``--fixtures`` the
script loads active deals for that city from the configured database.
It never calls the mailer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.newsletter import NewsletterSubscriber
from app.services.weekly_specials import (
    fetch_weekly_deals,
    render_weekly_issue,
    resolve_subscriber_place,
)
from app.services.weekly_specials_fixtures import galway_issue_fixtures


def _load_db_deals(country_code: str | None, city: str | None, location: str):
    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    place = resolve_subscriber_place(country_code, city, location)
    with session_factory() as session:
        return fetch_weekly_deals(session, place)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview Weekly Specials without sending.")
    parser.add_argument("--city", default="", help="Subscriber city, e.g. Galway")
    parser.add_argument("--country", default="", help="ISO country code, e.g. IE")
    parser.add_argument("--location", default="", help="Free-text location if city/country are unset")
    parser.add_argument("--name", default="Justin")
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Use the Galway junk/Irish sample instead of the database",
    )
    parser.add_argument("--html-file", default="", help="Also write the HTML body to this path")
    parser.add_argument("--text-file", default="", help="Also write the text body to this path")
    args = parser.parse_args(argv)

    city = args.city.strip() or None
    country = args.country.strip() or None
    location = args.location.strip() or city or ""
    if not city and not location:
        parser.error("Pass --city or --location")

    subscriber = NewsletterSubscriber(
        name=args.name.strip() or "there",
        surname="",
        email="preview@dineadeal.com",
        location=location,
        country_code=country.lower() if country else None,
        city=city,
        is_subscribed=True,
        unsubscribe_token="preview-not-sent",
    )
    if args.fixtures:
        deals = galway_issue_fixtures()
    else:
        deals = _load_db_deals(country, city, location)

    subject, text_body, html_body, selection, excluded = render_weekly_issue(
        subscriber,
        deals,
    )
    print("NOT SENT — preview only")
    print(f"Subscriber: {subscriber.name} <{subscriber.email}>")
    print(f"Location: {subscriber.location} ({country or 'unspecified'}, {city or 'unspecified'})")
    print(f"Scope: {selection.scope}")
    print(f"Local currency: {selection.local_currency}")
    print(f"Included ({len(selection.deals)}):")
    for deal in selection.deals:
        print(f"  - {deal.city}: {deal.title} — {deal.merchant_name}")
    print(f"Excluded ({len(excluded)}):")
    for deal, reason in excluded:
        print(f"  - {reason}: {deal.country_code}/{deal.city} {deal.merchant_name} / {deal.title}")
    print("\n===== TEXT =====\n")
    print(text_body)
    print("\n===== HTML =====\n")
    print(html_body)

    if args.text_file:
        Path(args.text_file).write_text(text_body, encoding="utf-8")
    if args.html_file:
        Path(args.html_file).write_text(html_body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
