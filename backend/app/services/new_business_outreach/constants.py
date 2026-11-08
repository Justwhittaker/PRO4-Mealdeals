"""Shared New Business Outreach identifiers."""

from __future__ import annotations

# marketing_contacts.source_segment for this weekly lead scrape.
NEW_BUSINESS_SEGMENT = "new_business_outreach"
# Rows written before migration 019. Outreach stays off for both.
LEGACY_SEGMENT_PREFIX = "fishy"
# Same value as NEW_BUSINESS_SEGMENT. Kept so older imports keep working
# while the stored segment name is new_business_outreach.
FISHY_FINGER_SEGMENT = NEW_BUSINESS_SEGMENT

RESTAURANTS = "Restaurants, Cafe's & Bistro's"
TAKEAWAYS = "Food Trucks & Takeaway's"
WINE_FARMS = "Wine Farms & Entertainment Venues"
TARGET_CATEGORIES = frozenset({RESTAURANTS, TAKEAWAYS, WINE_FARMS})

ON_SITE_REASONS = frozenset(
    {
        "already_on_site_name",
        "already_on_site_domain",
        "already_on_site_email",
        "existing_contact",
        "unsubscribed",
        "suppressed",
    }
)
