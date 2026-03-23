"""Build ContactCreate/ContactUpdate from User per docs/attribute_data_mapping.md (Contact table)."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.dto.contact import Contact, ContactCreate, ContactUpdate
from backend.models import User

# Payment fields included in COMMENTS per attribute_data_mapping
_COMMENTS_ATTRS = (
    "payment_company_name",
    "payment_bank_name",
    "payment_account",
    "payment_cor_account",
    "payment_card_number",
    "payment_inn",
    "payment_kpp",
    "payment_bik",
)


def _comments_from_user(user: User) -> str | None:
    """Build COMMENTS string from payment fields per attribute_data_mapping."""
    parts = [str(getattr(user, a, None)) for a in _COMMENTS_ATTRS if getattr(user, a, None)]
    return "; ".join(parts) if parts else None


def _name_parts(full_name: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (LAST_NAME, NAME, SECOND_NAME) from full_name per attribute_data_mapping split."""
    if not full_name or not full_name.strip():
        return None, None, None
    parts = [p for p in full_name.strip().split() if p]
    return (
        parts[0] if parts else None,
        parts[1] if len(parts) > 1 else None,
        parts[2] if len(parts) > 2 else None,
    )


def _contact_fields_from_user(user: User) -> dict[str, Any]:
    """Common contact field dict for create/update (avoids duplication)."""
    last_name, name, second_name = _name_parts(getattr(user, "full_name", None) or "")
    phone = getattr(user, "phone_number", None)
    email = getattr(user, "email", None)
    return {
        "ORIGIN_ID": str(user.id),
        "LAST_NAME": last_name,
        "NAME": name,
        "SECOND_NAME": second_name,
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}] if phone else None,
        "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else None,
        "ADDRESS_POSTAL_CODE": getattr(user, "postal", None),
        "ADDRESS_CITY": getattr(user, "city", None),
        "ADDRESS_REGION": getattr(user, "region", None),
        "ADDRESS": getattr(user, "street", None),
        "ADDRESS_2": getattr(user, "building", None),
        # "COMMENTS": _comments_from_user(user),
    }


def user_to_contact_create(user: User) -> ContactCreate:
    """Build ContactCreate from User per attribute_data_mapping Contact mapping."""
    return ContactCreate(**_contact_fields_from_user(user))


def user_to_contact_update(user: User) -> ContactUpdate:
    """Build ContactUpdate from User (same field mapping as create)."""
    return ContactUpdate(**_contact_fields_from_user(user))


# --- Reverse: Bitrix Contact → User ---


def _first_phone(contact: Contact) -> str | None:
    """Extract first phone value from Bitrix contact PHONE list."""
    phone = getattr(contact, "PHONE", None)
    if not phone or not isinstance(phone, list):
        return None
    first = phone[0] if phone else None
    if not isinstance(first, dict):
        return None
    return first.get("VALUE") or first.get("value")


def _first_email(contact: Contact) -> str | None:
    """Extract first email value from Bitrix contact EMAIL list."""
    email = getattr(contact, "EMAIL", None)
    if not email or not isinstance(email, list):
        return None
    first = email[0] if email else None
    if not isinstance(first, dict):
        return None
    return first.get("VALUE") or first.get("value")


def _comments_to_payment_fields(comments: str | None) -> dict[str, Any]:
    """Parse COMMENTS string back to payment fields (order matches _COMMENTS_ATTRS)."""
    if not comments or not comments.strip():
        return {}
    parts = [p.strip() for p in comments.split(";") if p.strip()]
    attrs = list(_COMMENTS_ATTRS)
    return {attrs[i]: parts[i] for i in range(min(len(parts), len(attrs)))}


def contact_to_user_update(contact: Contact) -> dict[str, Any]:
    """Build User update payload (dict) from Bitrix Contact. Reverse of user_to_contact_*."""
    last = getattr(contact, "LAST_NAME", None) or ""
    name = getattr(contact, "NAME", None) or ""
    second = getattr(contact, "SECOND_NAME", None) or ""
    full_name = " ".join(p for p in (last, name, second) if p).strip() or None

    payload = {
        "full_name": full_name,
        "phone_number": _first_phone(contact),
        "email": _first_email(contact),
        "postal": getattr(contact, "ADDRESS_POSTAL_CODE", None),
        "city": getattr(contact, "ADDRESS_CITY", None),
        "region": getattr(contact, "ADDRESS_REGION", None),
        "street": getattr(contact, "ADDRESS", None),
        "building": getattr(contact, "ADDRESS_2", None),
    }
    # payload.update(_comments_to_payment_fields(getattr(contact, "COMMENTS", None)))
    return {k: v for k, v in payload.items() if v is not None}
