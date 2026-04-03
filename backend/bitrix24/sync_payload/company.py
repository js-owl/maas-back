"""Build CompanyCreate/CompanyUpdate from User for legal-entity sync.

Recommended Bitrix layout:
- company card: only visible company data required by MaaS business flow
- legal/tax/bank data: requisite + bank detail + requisite address
"""

from __future__ import annotations

from typing import Any

from backend.bitrix24.dto.company import CompanyCreate, CompanyUpdate
from backend.models import User


def _compact_join(*parts: Any, sep: str = ", ") -> str | None:
    values = [str(p).strip() for p in parts if p is not None and str(p).strip()]
    return sep.join(values) if values else None


def company_title(user: User) -> str:
    return (
        getattr(user, "payment_company_name", None)
        or getattr(user, "company", None)
        or getattr(user, "username", None)
        or f"User {getattr(user, 'id', '')}"
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
        "ADDRESS_LEGAL": "",
    }


def _company_fields_from_user(user: User) -> dict[str, Any]:
    email = getattr(user, "email", None)
    phone = getattr(user, "phone_number", None)
    payload: dict[str, Any] = {
        "TITLE": company_title(user),
        "ORIGIN_ID": str(user.id),
        "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}] if phone else None,
        "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else None,
    }
    return {k: v for k, v in payload.items() if v is not None}


def user_to_company_create(user: User) -> CompanyCreate:
    return CompanyCreate(**_company_fields_from_user(user))


def user_to_company_update(user: User) -> CompanyUpdate:
    payload = _company_fields_from_user(user)
    payload.update(_legacy_address_clear_fields())
    return CompanyUpdate(**payload)
