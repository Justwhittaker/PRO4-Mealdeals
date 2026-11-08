"""Email quality for Fishy Finger Sub leads.

Preferred addresses, highest score first: owner, marketing, a named person,
hello, info, then bookings / reservations. Anything on that list is stored.

Rejected outright (score 0, not stored, not emailed):

- noreply, no-reply, donotreply, mailer-daemon
- privacy, legal, abuse
- jobs, careers, recruitment
- support@ (and help@) on a platform or booking-vendor domain
- any address on a third-party booking or platform domain, even if the local
  part looks like a person (``jane@opentable.com``)

``support@`` on the venue's own domain is kept, at a lower score than
info/hello, because some independents only publish that inbox.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.marketing_contacts import _clean_email

# Local-part (before +tag) → score. Higher is a better outreach target.
_ROLE_SCORES: dict[str, int] = {
    "owner": 96,
    "marketing": 94,
    "hello": 82,
    "info": 80,
    "bookings": 78,
    "booking": 78,
    "reservations": 78,
    "reservation": 76,
    "enquiries": 74,
    "enquiry": 74,
    "inquiries": 74,
    "inquiry": 74,
    "contact": 72,
}

_NAMED_PERSON_SCORE = 88
_SINGLE_NAME_SCORE = 86
_OTHER_ACCEPTED_SCORE = 50
_OWN_DOMAIN_SUPPORT_SCORE = 45

_REJECT_LOCAL_RE = re.compile(
    r"^(?:"
    r"no[-_.]?reply|do[-_.]?not[-_.]?reply|donotreply|"
    r"mailer[-_.]?daemon|postmaster|"
    r"privacy|legal|abuse|"
    r"jobs|job|careers?|recruit(?:ment|ing)?|"
    r"human[-_.]?resources|talent|press|compliance|gdpr|dpo|"
    r"admin|webmaster"
    r")(?:[._+-].*)?$",
    re.I,
)

_NAMED_PERSON_RE = re.compile(r"^[a-z]{2,}(?:[._-][a-z]{2,})+$")
_SINGLE_NAME_RE = re.compile(r"^[a-z]{3,}$")

# Booking vendors, review sites, site builders, and ticket platforms.
# Matched on the email domain and its subdomains. Consumer inboxes
# (gmail, outlook, icloud) are not in this set.
PLATFORM_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "opentable.com",
        "opentable.co.uk",
        "resy.com",
        "thefork.com",
        "thefork.co.uk",
        "thefork.ie",
        "bookatable.com",
        "bookatable.co.uk",
        "quandoo.com",
        "quandoo.co.uk",
        "sevenrooms.com",
        "designmynight.com",
        "toasttab.com",
        "squareup.com",
        "square.site",
        "tripadvisor.com",
        "tripadvisor.co.uk",
        "tripadvisor.ie",
        "yelp.com",
        "yelp.co.uk",
        "yelp.ie",
        "facebook.com",
        "fb.com",
        "instagram.com",
        "booking.com",
        "expedia.com",
        "eventbrite.com",
        "wix.com",
        "wixsite.com",
        "squarespace.com",
        "shopify.com",
        "godaddy.com",
        "wordpress.com",
        "mailchimp.com",
        "hubspot.com",
        "zendesk.com",
        "freshdesk.com",
        "intercom.io",
        "google.com",
        "linktr.ee",
        "linktree.com",
    }
)

_FILE_TLDS = frozenset({"png", "jpg", "jpeg", "gif", "webp", "svg", "css", "js"})


@dataclass(frozen=True)
class EmailVerdict:
    email: str | None
    score: int
    accepted: bool
    reason: str


def is_platform_email_domain(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower().strip(".").removeprefix("www.")
    for platform in PLATFORM_EMAIL_DOMAINS:
        if host == platform or host.endswith("." + platform):
            return True
    return False


def _split(email: str | None) -> tuple[str, str] | None:
    cleaned = _clean_email(email)
    if not cleaned or "@" not in cleaned:
        return None
    local, domain = cleaned.split("@", 1)
    local = local.split("+", 1)[0].strip(".")
    domain = domain.lower().strip(".")
    if not local or not domain or "." not in domain:
        return None
    tld = domain.rsplit(".", 1)[-1]
    if tld in _FILE_TLDS:
        return None
    return local, domain


def score_email(email: str | None) -> EmailVerdict:
    """Score one address. ``accepted`` is false when the address must be dropped."""
    parsed = _split(email)
    if parsed is None:
        return EmailVerdict(email=None, score=0, accepted=False, reason="invalid")
    local, domain = parsed
    cleaned = f"{local}@{domain}"
    if is_platform_email_domain(domain):
        if local in {"support", "help"}:
            return EmailVerdict(cleaned, 0, False, "platform_support")
        return EmailVerdict(cleaned, 0, False, "platform_domain")
    if _REJECT_LOCAL_RE.match(local):
        return EmailVerdict(cleaned, 0, False, "rejected_local")
    if local in {"support", "help"}:
        return EmailVerdict(cleaned, _OWN_DOMAIN_SUPPORT_SCORE, True, "own_domain_support")

    head = re.split(r"[._-]", local, maxsplit=1)[0]
    if head in _ROLE_SCORES and (
        local == head or local.startswith((f"{head}.", f"{head}_", f"{head}-"))
    ):
        return EmailVerdict(cleaned, _ROLE_SCORES[head], True, f"role:{head}")
    if _NAMED_PERSON_RE.match(local):
        return EmailVerdict(cleaned, _NAMED_PERSON_SCORE, True, "named_person")
    if _SINGLE_NAME_RE.match(local) and head not in _ROLE_SCORES:
        return EmailVerdict(cleaned, _SINGLE_NAME_SCORE, True, "named_person")
    return EmailVerdict(cleaned, _OTHER_ACCEPTED_SCORE, True, "other")


def pick_best_email(addresses: tuple[str, ...] | list[str]) -> EmailVerdict:
    """Highest accepted score. Rejected addresses are ignored, not stored."""
    best: EmailVerdict | None = None
    saw_rejected = False
    for address in addresses:
        verdict = score_email(address)
        if not verdict.accepted:
            if verdict.reason != "invalid":
                saw_rejected = True
            continue
        if best is None or verdict.score > best.score:
            best = verdict
    if best is not None:
        return best
    if saw_rejected:
        return EmailVerdict(None, 0, False, "rejected")
    return EmailVerdict(None, 0, False, "missing")
