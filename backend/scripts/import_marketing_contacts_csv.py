#!/usr/bin/env python3
"""Import or refresh marketing_contacts from a CSV export.

Usage:
  cd backend
  python scripts/import_marketing_contacts_csv.py /path/to/marketing_contacts_full.csv

Expected columns (header row required):
  business_name, phone, email, website, about_blurb, country_code, city,
  venue_category, source_url, last_scraped_at
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python scripts/import_marketing_contacts_csv.py` from backend/ or Docker /app.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.services.marketing_contacts import upsert_marketing_contact


def _optional_bool(raw: str | None) -> bool | None:
    text = (raw or "").strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return None


def _optional_dt(raw: str | None) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        return 1

    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    imported = 0
    skipped = 0

    with path.open(newline="", encoding="utf-8") as handle, Session() as session:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("business_name") or "").strip()
            if not name:
                skipped += 1
                continue
            country = (row.get("country_code") or "XX").strip()
            result = upsert_marketing_contact(
                session,
                business_name=name,
                website=row.get("website") or None,
                phone=row.get("phone") or None,
                email=row.get("email") or None,
                about_blurb=row.get("about_blurb") or None,
                country_code=country,
                city=row.get("city") or None,
                source_url=row.get("source_url") or None,
                venue_category=row.get("venue_category") or None,
                source_segment=row.get("source_segment") or None,
                lead_zone=row.get("lead_zone") or None,
                email_quality_score=(
                    int(row["email_quality_score"])
                    if (row.get("email_quality_score") or "").strip()
                    else None
                ),
                has_site_specials=_optional_bool(row.get("has_site_specials")),
                specials_checked_at=_optional_dt(row.get("specials_checked_at")),
            )
            if result is None:
                skipped += 1
            else:
                imported += 1
        session.commit()

    print({"imported": imported, "skipped": skipped, "source": str(path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
