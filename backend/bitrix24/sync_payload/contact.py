"""Build ContactCreate/ContactUpdate payloads from User."""

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
    parts = [str(getattr(user, a, None)) for a in _COMMENTS_ATTRS if getattr(user, a, None)]
    return "; ".join(parts) if parts else None


def _name_parts(full_name: str | None) -> tuple[str | None, str | None, str | None]:
    if not full_name or not full_name.strip():
        return None, None, None
    parts = [p for p in full_name.strip().split() if p]
    return (
        parts[0] if parts else None,
        parts[1] if len(parts) > 1 else None,
        parts[2] if len(parts) > 2 else None,
    )


def _legacy_address_clear_fields() -> dict[str, Any]:
    return {
        "ADDRESS": "",
        "ADDRESS_2": "",
        "ADDRESS_CITY": "",
        "ADDRESS_POSTAL_CODE": "",
        "ADDRESS_REGION": "",
        "ADDRESS_PROVINCE": "",
        "ADDRESS_COUNTRY": "",
        "ADDRESS_COUNTRY_CODE": "",
    }


def _contact_fields_from_user(user: User) -> dict[str, Any]:
    last_name, name, second_name = _name_parts(getattr(user, "full_name", None) or "")
    phone = getattr(user, "personal_phone_number", None)
    email = getattr(user, "personal_email", None)
    return {
        "ORIGIN_ID": str(user.id),
        "LAST_NAME": last_name,
        "NAME": name,
        "SECOND_NAME": second_name,
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "MOBILE"}] if phone else None,
        "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else None,
    }


def user_to_contact_create(user: User) -> ContactCreate:
    return ContactCreate(**_contact_fields_from_user(user))


def user_to_contact_update(user: User) -> ContactUpdate:
    payload = _contact_fields_from_user(user)
    payload.update(_legacy_address_clear_fields())
    return ContactUpdate(**payload)


def has_company_contact_payload(user: User) -> bool:
    return bool(getattr(user, "full_name", None) and getattr(user, "personal_phone_number", None))


def _company_contact_fields_from_user(user: User, *, company_id: int) -> dict[str, Any]:
    last_name, name, second_name = _name_parts(getattr(user, "full_name", None) or "")
    personal_phone = getattr(user, "personal_phone_number", None)
    personal_email = getattr(user, "personal_email", None)
    return {
        "ORIGIN_ID": str(user.id),
        "LAST_NAME": last_name,
        "NAME": name,
        "SECOND_NAME": second_name,
        "PHONE": [{"VALUE": personal_phone, "VALUE_TYPE": "MOBILE"}] if personal_phone else None,
        "EMAIL": [{"VALUE": personal_email, "VALUE_TYPE": "WORK"}] if personal_email else None,
        "COMPANY_ID": int(company_id),
        "COMPANY_IDS": [int(company_id)],
    }


def user_to_company_contact_create(user: User, *, company_id: int) -> ContactCreate:
    return ContactCreate(**_company_contact_fields_from_user(user, company_id=company_id))


def user_to_company_contact_update(user: User, *, company_id: int) -> ContactUpdate:
    payload = _company_contact_fields_from_user(user, company_id=company_id)
    payload.update(_legacy_address_clear_fields())
    return ContactUpdate(**payload)


# --- Reverse: Bitrix Contact → User ---


def _first_phone(contact: Contact) -> str | None:
    phone = getattr(contact, "PHONE", None)
    if not phone or not isinstance(phone, list):
        return None
    first = phone[0] if phone else None
    if not isinstance(first, dict):
        return None
    return first.get("VALUE") or first.get("value")


def _first_email(contact: Contact) -> str | None:
    email = getattr(contact, "EMAIL", None)
    if not email or not isinstance(email, list):
        return None
    first = email[0] if email else None
    if not isinstance(first, dict):
        return None
    return first.get("VALUE") or first.get("value")


def _comments_to_payment_fields(comments: str | None) -> dict[str, Any]:
    if not comments or not comments.strip():
        return {}
    parts = [p.strip() for p in comments.split(";") if p.strip()]
    attrs = list(_COMMENTS_ATTRS)
    return {attrs[i]: parts[i] for i in range(min(len(parts), len(attrs)))}


def contact_to_user_update(contact: Contact) -> dict[str, Any]:
    last = getattr(contact, "LAST_NAME", None) or ""
    name = getattr(contact, "NAME", None) or ""
    second = getattr(contact, "SECOND_NAME", None) or ""
    full_name = " ".join(p for p in (last, name, second) if p).strip() or None

    payload = {
        "full_name": full_name,
        "personal_phone_number": _first_phone(contact),
        "personal_email": _first_email(contact),
        "postal": getattr(contact, "ADDRESS_POSTAL_CODE", None),
        "city": getattr(contact, "ADDRESS_CITY", None),
        "region": getattr(contact, "ADDRESS_REGION", None),
        "street": getattr(contact, "ADDRESS", None),
        "building": getattr(contact, "ADDRESS_2", None),
    }
    return {k: v for k, v in payload.items() if v is not None}
