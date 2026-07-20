"""Async SMTP sender for auth emails (email verification + password recovery)."""

from __future__ import annotations

import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from backend.core.config import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TLS_VERIFY,
    SMTP_USER,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def _make_tls_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not SMTP_TLS_VERIFY:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def send_auth_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    from_addr: str | None = None,
) -> None:
    """Send an HTML email via SMTP STARTTLS.

    Uses SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD from config.
    TLS certificate verification is controlled by SMTP_TLS_VERIFY (default off).
    """
    sender = from_addr or SMTP_FROM

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER or None,
        password=SMTP_PASSWORD or None,
        start_tls=True,
        tls_context=_make_tls_context(),
    )
    logger.debug("Auth email sent to %s via %s:%d", to, SMTP_HOST, SMTP_PORT)
