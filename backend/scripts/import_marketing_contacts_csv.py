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
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.services.marketing_contacts import upsert_marketing_contact


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
