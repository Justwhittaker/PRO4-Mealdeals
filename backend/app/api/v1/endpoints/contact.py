"""Public contact form — emails Justin via Resend/SMTP helper."""

from __future__ import annotations

import html
import logging

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.contact import ContactMessageCreate, ContactMessageResponse
from app.services.email import is_email_configured, send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_contact_message(
    payload: ContactMessageCreate,
) -> ContactMessageResponse:
    settings = get_settings()
    to_email = (settings.contact_to_email or "").strip() or "just.whittaker@gmail.com"

    if not is_email_configured(settings):
        logger.error("Contact form rejected: email transport not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Contact email is not configured yet (set RESEND_API_KEY, or "
                "SMTP_HOST on a paid Render instance). Please try again later."
            ),
        )

    name = payload.name.strip()
    surname = payload.surname.strip()
    email = str(payload.email).strip().lower()
    phone = payload.phone.strip()
    business = (payload.business or "").strip()
    title = payload.title.strip()
    description = payload.description.strip()

    subject = f"[Dine A Deal contact] {title}"
    text_body = "\n".join(
        [
            "New contact form submission from dineadeal.com",
            "",
            f"Name: {name} {surname}",
            f"Email: {email}",
            f"Phone: {phone}",
            f"Business: {business or '(not provided)'}",
            f"Title: {title}",
            "",
            "Description:",
            description,
        ]
    )
    html_body = f"""
    <h2>New contact form submission</h2>
    <p><strong>Name:</strong> {html.escape(name)} {html.escape(surname)}<br/>
    <strong>Email:</strong> {html.escape(email)}<br/>
    <strong>Phone:</strong> {html.escape(phone)}<br/>
    <strong>Business:</strong> {html.escape(business) if business else "(not provided)"}<br/>
    <strong>Title:</strong> {html.escape(title)}</p>
    <p><strong>Description</strong></p>
    <p>{html.escape(description).replace(chr(10), "<br/>")}</p>
    """

    delivered = send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    if not delivered:
        logger.error("Contact form email failed for %s", email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Could not deliver your message. Please try again shortly. "
                "On Render free, outbound SMTP is blocked — set RESEND_API_KEY."
            ),
        )

    return ContactMessageResponse(
        message="Thanks — your message has been sent. We'll get back to you soon.",
        delivered=True,
    )
