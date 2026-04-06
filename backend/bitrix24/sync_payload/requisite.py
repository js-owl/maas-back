"""Build Bitrix requisite/bank-detail/address DTOs from legal User."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.dto.address import AddressUpsert
from backend.bitrix24.dto.bank_detail import BankDetailCreate, BankDetailUpdate
from backend.bitrix24.dto.requisite import RequisiteCreate, RequisiteUpdate
from backend.bitrix24.sync_payload.company import company_title
from backend.models import User

CRM_OWNER_TYPE_CONTACT = 3
CRM_OWNER_TYPE_COMPANY = 4
CRM_OWNER_TYPE_REQUISITE = 8
ADDRESS_TYPE_FACT = 1
ADDRESS_TYPE_LEGAL = 6
RU_COUNTRY_ID = 1
DEFAULT_ACCOUNT_CURRENCY = "RUR"


def _compact_join(*parts: Any, sep: str = ", ") -> str | None:
    values = [str(p).strip() for p in parts if p is not None and str(p).strip()]
    return sep.join(values) if values else None


def _rq_company_full_name(user: User) -> str:
    return (
        getattr(user, "payment_company_name", None)
        or getattr(user, "company", None)
        or company_title(user)
    )


def _requisite_name(user: User) -> str:
    return f"Реквизиты {company_title(user)}"


def _contact_requisite_name(user: User) -> str:
    full_name = getattr(user, "full_name", None)
    if full_name and str(full_name).strip():
        return f"Адрес {str(full_name).strip()}"
    return f"Адрес пользователя {getattr(user, 'id', '')}"


def _bank_detail_name(user: User) -> str:
    return f"Банковские реквизиты {company_title(user)}"


def _requisite_fields_from_user(
    user: User,
    *,
    company_id: int,
    preset_id: int,
) -> dict[str, Any]:
    return {
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY,
        "ENTITY_ID": int(company_id),
        "PRESET_ID": int(preset_id),
        "NAME": _requisite_name(user),
        "ACTIVE": "Y",
        "RQ_COMPANY_FULL_NAME": _rq_company_full_name(user),
        "RQ_INN": getattr(user, "payment_inn", None),
        "RQ_KPP": getattr(user, "payment_kpp", None),
    }


def user_to_requisite_create(user: User, *, company_id: int, preset_id: int) -> RequisiteCreate:
    payload = {k: v for k, v in _requisite_fields_from_user(user, company_id=company_id, preset_id=preset_id).items() if v is not None}
    return RequisiteCreate(**payload)


def user_to_requisite_update(user: User, *, company_id: int, preset_id: int) -> RequisiteUpdate:
    payload = {k: v for k, v in _requisite_fields_from_user(user, company_id=company_id, preset_id=preset_id).items() if v is not None}
    payload.pop("ENTITY_TYPE_ID", None)
    payload.pop("ENTITY_ID", None)
    payload.pop("PRESET_ID", None)
    return RequisiteUpdate(**payload)




def _contact_requisite_fields_from_user(
    user: User,
    *,
    contact_id: int,
    preset_id: int,
) -> dict[str, Any]:
    return {
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_CONTACT,
        "ENTITY_ID": int(contact_id),
        "PRESET_ID": int(preset_id),
        "NAME": _contact_requisite_name(user),
        "ACTIVE": "Y",
        "ADDRESS_ONLY": "Y",
    }


def user_to_contact_requisite_create(user: User, *, contact_id: int, preset_id: int) -> RequisiteCreate:
    payload = {
        k: v
        for k, v in _contact_requisite_fields_from_user(user, contact_id=contact_id, preset_id=preset_id).items()
        if v is not None
    }
    return RequisiteCreate(**payload)


def user_to_contact_requisite_update(user: User, *, contact_id: int, preset_id: int) -> RequisiteUpdate:
    payload = {
        k: v
        for k, v in _contact_requisite_fields_from_user(user, contact_id=contact_id, preset_id=preset_id).items()
        if v is not None
    }
    payload.pop("ENTITY_TYPE_ID", None)
    payload.pop("ENTITY_ID", None)
    payload.pop("PRESET_ID", None)
    return RequisiteUpdate(**payload)

def _bank_detail_fields_from_user(user: User, *, requisite_id: int, country_id: int = RU_COUNTRY_ID) -> dict[str, Any]:
    return {
        "ENTITY_ID": int(requisite_id),
        "COUNTRY_ID": int(country_id),
        "NAME": _bank_detail_name(user),
        "ACTIVE": "Y",
        "RQ_BANK_NAME": getattr(user, "payment_bank_name", None),
        "RQ_BIK": getattr(user, "payment_bik", None),
        "RQ_ACC_NUM": getattr(user, "payment_account", None),
        "RQ_COR_ACC_NUM": getattr(user, "payment_cor_account", None),
        "RQ_ACC_CURRENCY": DEFAULT_ACCOUNT_CURRENCY,
    }


def _has_bank_payload(user: User) -> bool:
    return any(
        getattr(user, attr, None)
        for attr in (
            "payment_bank_name",
            "payment_bik",
            "payment_account",
            "payment_cor_account",
        )
    )


def user_to_bank_detail_create(
    user: User,
    *,
    requisite_id: int,
    country_id: int = RU_COUNTRY_ID,
) -> BankDetailCreate | None:
    if not _has_bank_payload(user):
        return None
    payload = {k: v for k, v in _bank_detail_fields_from_user(user, requisite_id=requisite_id, country_id=country_id).items() if v is not None}
    return BankDetailCreate(**payload)


def user_to_bank_detail_update(
    user: User,
    *,
    requisite_id: int,
    country_id: int = RU_COUNTRY_ID,
) -> BankDetailUpdate | None:
    if not _has_bank_payload(user):
        return None
    payload = {k: v for k, v in _bank_detail_fields_from_user(user, requisite_id=requisite_id, country_id=country_id).items() if v is not None}
    payload.pop("ENTITY_ID", None)
    return BankDetailUpdate(**payload)


def has_address_payload(user: User) -> bool:
    return any(
        getattr(user, attr, None)
        for attr in ("street", "building", "city", "postal", "region")
    )


def user_to_legal_address(
    user: User,
    *,
    requisite_id: int,
    type_id: int = ADDRESS_TYPE_LEGAL,
    country_code: str = "RU",
    country_name: str = "Россия",
) -> AddressUpsert | None:
    if not has_address_payload(user):
        return None
    address_1 = _compact_join(getattr(user, "street", None), getattr(user, "building", None))
    payload = {
        "TYPE_ID": int(type_id),
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_REQUISITE,
        "ENTITY_ID": int(requisite_id),
        "ADDRESS_1": address_1,
        "ADDRESS_2": getattr(user, "office", None),
        "CITY": getattr(user, "city", None),
        "POSTAL_CODE": getattr(user, "postal", None),
        "PROVINCE": getattr(user, "region", None),
        "COUNTRY": country_name,
        "COUNTRY_CODE": country_code,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    return AddressUpsert(**payload)


def user_to_contact_address(
    user: User,
    *,
    requisite_id: int,
    type_id: int = ADDRESS_TYPE_FACT,
    country_code: str = "RU",
    country_name: str = "Россия",
) -> AddressUpsert | None:
    if not has_address_payload(user):
        return None
    address_1 = _compact_join(getattr(user, "street", None), getattr(user, "building", None))
    payload = {
        "TYPE_ID": int(type_id),
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_REQUISITE,
        "ENTITY_ID": int(requisite_id),
        "ADDRESS_1": address_1,
        "ADDRESS_2": getattr(user, "office", None),
        "CITY": getattr(user, "city", None),
        "POSTAL_CODE": getattr(user, "postal", None),
        "PROVINCE": getattr(user, "region", None),
        "COUNTRY": country_name,
        "COUNTRY_CODE": country_code,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    return AddressUpsert(**payload)
