"""Build ContactCreate/ContactUpdate from User per docs/attribute_data_mapping.md (Contact table)."""

from __future__ import annotations

from backend.bitrix24.dto.contact import ContactCreate, ContactUpdate

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


def _comments_from_user(user) -> str | None:
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


def _contact_fields_from_user(user) -> dict:
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
        "COMMENTS": _comments_from_user(user),
    }


def user_to_contact_create(user) -> ContactCreate:
    """Build ContactCreate from User per attribute_data_mapping Contact mapping."""
    return ContactCreate(**_contact_fields_from_user(user))


def user_to_contact_update(user) -> ContactUpdate:
    """Build ContactUpdate from User (same field mapping as create)."""
    return ContactUpdate(**_contact_fields_from_user(user))
