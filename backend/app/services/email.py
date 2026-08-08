"""Transactional email helper.

Prefer Resend (HTTPS) when RESEND_API_KEY is set — required on Render free
web services, which block outbound SMTP ports 25/465/587. Fall back to SMTP
when Resend is unset (local/dev or paid Render instances).
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_SMTP_TIMEOUT_SECONDS = 10
_RESEND_API_URL = "https://api.resend.com/emails"


def is_email_configured(settings: Optional[Settings] = None) -> bool:
    """True when Resend or an allowed SMTP transport is configured."""
    cfg = settings or get_settings()
    if cfg.resend_api_key.strip():
        return True
    if not cfg.smtp_host.strip():
        return False
    # Local/dev: SMTP is fine. Production: only when SMTP_ALLOW=true (paid Render).
    if cfg.app_env in {"development", "test"}:
        return True
    return bool(cfg.smtp_allow)


def send_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> bool:
    """
    Send an email via Resend (preferred) or SMTP.

    Returns True if sent (or dry-run logged). Returns False only on delivery failure.
    When neither Resend nor allowed SMTP is configured, logs and returns True in
    development/test; False in staging/production.
    """
    settings = get_settings()

    if settings.resend_api_key.strip():
        return _send_via_resend(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    smtp_ok = bool(settings.smtp_host.strip()) and (
        settings.app_env in {"development", "test"} or settings.smtp_allow
    )
    if smtp_ok:
        return _send_via_smtp(
            settings=settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    if settings.smtp_host.strip() and not settings.smtp_allow:
        logger.warning(
            "[email] SMTP_HOST is set but SMTP_ALLOW is false — skipping SMTP "
            "(Render free blocks ports 25/465/587). Set RESEND_API_KEY or "
            "SMTP_ALLOW=true on a paid instance. to=%s subject=%s",
            to_email,
            subject,
        )

    logger.warning(
        "[email-dry-run] No RESEND_API_KEY or allowed SMTP — not delivering to=%s subject=%s\n%s",
        to_email,
        subject,
        text_body[:2000],
    )
    if settings.app_env in {"development", "test"}:
        return True
    return False


def _send_via_resend(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str],
) -> bool:
    from_addr = (settings.resend_from_email or "").strip() or settings.smtp_from_email
    payload: dict[str, object] = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    try:
        response = httpx.post(
            _RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        if response.is_success:
            logger.info("Email sent via Resend to %s subject=%s", to_email, subject)
            return True
        logger.error(
            "Resend failed status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        return False
    except Exception:
        logger.exception("Failed to send email via Resend to %s", to_email)
        return False


def _send_via_smtp(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str],
) -> bool:
    from_addr = settings.smtp_from_email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT_SECONDS
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT_SECONDS
            ) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(from_addr, [to_email], msg.as_string())
        logger.info("Email sent via SMTP to %s subject=%s", to_email, subject)
        return True
    except OSError:
        logger.exception(
            "SMTP connect failed to %s:%s (Render free web services block ports "
            "25/465/587 — set RESEND_API_KEY or upgrade the instance)",
            settings.smtp_host,
            settings.smtp_port,
        )
        return False
    except Exception:
        logger.exception("Failed to send email via SMTP to %s", to_email)
        return False
