"""Rendering helpers for authentication HTML emails."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Literal

AuthEmailTemplateKind = Literal["confirmation", "recovery"]

TEMPLATE_FILES: dict[AuthEmailTemplateKind, str] = {
    "confirmation": "email_verification.html",
    "recovery": "password_recovery.html",
}
TEMPLATE_DIR = Path(__file__).with_name("templates")


def format_expiration_datetime(value: datetime) -> str:
    """Format a link expiration timestamp for email copy."""
    return value.astimezone().strftime("%d.%m.%Y %H:%M %Z").strip()


def render_auth_email_template(
    kind: AuthEmailTemplateKind,
    *,
    action_url: str,
    expires_at: datetime,
) -> str:
    template_name = TEMPLATE_FILES[kind]
    template = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    escaped_url = escape(action_url, quote=True)
    escaped_expiration = escape(format_expiration_datetime(expires_at))

    placeholders = {
        "{{ACTION_URL}}": escaped_url,
        "{{CONFIRMATION_URL}}": escaped_url,
        "{{RESET_PASSWORD_URL}}": escaped_url,
        "{{EXPIRATION_DATE}}": escaped_expiration,
    }
    for placeholder, value in placeholders.items():
        template = template.replace(placeholder, value)
    return template
