"""Startup reconciliation for Bitrix24 managed My Company and its requisites."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto.address import AddressUpsert
from backend.bitrix24.dto.bank_detail import BankDetailCreate, BankDetailUpdate
from backend.bitrix24.dto.company import CompanyCreate, CompanyUpdate
from backend.bitrix24.dto.requisite import RequisiteCreate, RequisiteUpdate
from backend.bitrix24.repositories.mapping_repository import upsert_mapping, get_mapping_by_maas_id
from backend.bitrix24.services.address import AddressService
from backend.bitrix24.services.bank_detail import BankDetailService
from backend.bitrix24.services.company import CompanyService
from backend.bitrix24.services.requisite import RequisiteService
from backend.bitrix24.sync_payload.requisite import (
    ADDRESS_TYPE_LEGAL,
    CRM_OWNER_TYPE_COMPANY,
    CRM_OWNER_TYPE_REQUISITE,
    RU_COUNTRY_ID,
)
from backend.core.config import MYCOMPANY_REQUISITES
from backend.utils.logging import get_logger

logger = get_logger(__name__)

MYCOMPANY_MAAS_ID = 0
MYCOMPANY_ENTITY_TYPE = "mycompany"
MYCOMPANY_REQUISITE_ENTITY_TYPE = "mycompany_requisite"
MYCOMPANY_BANK_DETAIL_ENTITY_TYPE = "mycompany_bank_detail"


def _requisities_config(name: str, default: str | None = None) -> str | None:
    value = MYCOMPANY_REQUISITES.get(name, None)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_int_env(name: str, default: int | None = None) -> int | None:
    return _safe_int(os.getenv(name), default)


def _mf(value: str | None, value_type: str = "WORK") -> list[dict[str, str]] | None:
    if not value:
        return None
    return [{"VALUE": value, "VALUE_TYPE": value_type}]


def _has_any_company_config() -> bool:
    keys = (
        "BITRIX_MYCOMPANY_TITLE",
        "BITRIX_MYCOMPANY_RQ_COMPANY_FULL_NAME",
        "BITRIX_MYCOMPANY_RQ_COMPANY_NAME",
        "BITRIX_MYCOMPANY_EMAIL",
        "BITRIX_MYCOMPANY_PHONE",
        "BITRIX_MYCOMPANY_RQ_INN",
        "BITRIX_MYCOMPANY_RQ_KPP",
        "BITRIX_MYCOMPANY_BANK_NAME",
        "BITRIX_MYCOMPANY_ACCOUNT",
    )
    return any(_requisities_config(k) for k in keys)


async def _resolve_company_preset_id(client: BitrixClient, *, country_id: int) -> int | None:
    preset_id = _safe_int_env("BITRIX_MYCOMPANY_REQUISITE_PRESET_ID")
    if preset_id:
        return int(preset_id)

    candidate_filters = [
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY, "COUNTRY_ID": int(country_id)},
        {"COUNTRY_ID": int(country_id)},
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY},
        None,
    ]
    seen: set[int] = set()
    for filter_payload in candidate_filters:
        try:
            result = await client.call(
                "crm.requisite.preset.list",
                {"filter": filter_payload, "order": {"SORT": "ASC"}, "select": ["ID", "COUNTRY_ID", "NAME"]} if filter_payload else {"order": {"SORT": "ASC"}, "select": ["ID", "COUNTRY_ID", "NAME"]},
            )
        except Exception as exc:
            logger.warning("Failed to resolve my company requisite preset list with filter=%s: %s", filter_payload, exc)
            continue
        rows = result if isinstance(result, list) else []
        for row in rows:
            row_id = _safe_int((row or {}).get("ID"))
            if row_id and row_id not in seen:
                seen.add(row_id)
                return int(row_id)
    return None


def _company_create_payload() -> CompanyCreate:
    payload = {
        "TITLE": _requisities_config("BITRIX_MYCOMPANY_TITLE") or _requisities_config("BITRIX_MYCOMPANY_RQ_COMPANY_FULL_NAME"),
        "IS_MY_COMPANY": "Y",
        "PHONE": _mf(_requisities_config("BITRIX_MYCOMPANY_PHONE")),
        "EMAIL": _mf(_requisities_config("BITRIX_MYCOMPANY_EMAIL")),
        # "ORIGINATOR_ID": _env("BITRIX_MYCOMPANY_ORIGINATOR_ID", "maas"),
        # "ORIGIN_ID": _env("BITRIX_MYCOMPANY_ORIGIN_ID", "mycompany"),
    }
    return CompanyCreate(**{k: v for k, v in payload.items() if v is not None})


def _company_update_payload() -> CompanyUpdate:
    payload = _company_create_payload().model_dump(exclude_none=True)
    return CompanyUpdate(**payload)


def _requisite_create_payload(*, company_id: int, preset_id: int) -> RequisiteCreate:
    payload = {
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY,
        "ENTITY_ID": int(company_id),
        "PRESET_ID": int(preset_id),
        "NAME": _requisities_config("BITRIX_MYCOMPANY_REQUISITE_NAME") or "Реквизиты моей организации",
        "ACTIVE": "Y",
        "RQ_COMPANY_FULL_NAME": _requisities_config("BITRIX_MYCOMPANY_RQ_COMPANY_FULL_NAME") or _requisities_config("BITRIX_MYCOMPANY_TITLE"),
        "RQ_COMPANY_NAME": _requisities_config("BITRIX_MYCOMPANY_RQ_COMPANY_NAME"),
        "RQ_CONTACT": _requisities_config("BITRIX_MYCOMPANY_RQ_CONTACT"),
        "RQ_EMAIL": _requisities_config("BITRIX_MYCOMPANY_RQ_EMAIL") or _requisities_config("BITRIX_MYCOMPANY_EMAIL"),
        "RQ_PHONE": _requisities_config("BITRIX_MYCOMPANY_RQ_PHONE") or _requisities_config("BITRIX_MYCOMPANY_PHONE"),
        "RQ_INN": _requisities_config("BITRIX_MYCOMPANY_RQ_INN"),
        "RQ_KPP": _requisities_config("BITRIX_MYCOMPANY_RQ_KPP"),
        "RQ_OGRN": _requisities_config("BITRIX_MYCOMPANY_RQ_OGRN"),
        # "ORIGINATOR_ID": _env("BITRIX_MYCOMPANY_ORIGINATOR_ID", "maas"),
        # "ORIGIN_ID": _env("BITRIX_MYCOMPANY_ORIGIN_ID", "mycompany"),
    }
    return RequisiteCreate(**{k: v for k, v in payload.items() if v is not None})


def _requisite_update_payload(*, company_id: int, preset_id: int) -> RequisiteUpdate:
    payload = _requisite_create_payload(company_id=company_id, preset_id=preset_id).model_dump(exclude_none=True)
    for key in ("ENTITY_TYPE_ID", "ENTITY_ID", "PRESET_ID"):
        payload.pop(key, None)
    return RequisiteUpdate(**payload)


def _bank_detail_create_payload(*, requisite_id: int, country_id: int) -> BankDetailCreate | None:
    payload = {
        "ENTITY_ID": int(requisite_id),
        "COUNTRY_ID": int(country_id),
        "NAME": _requisities_config("BITRIX_MYCOMPANY_BANK_DETAIL_NAME") or "Банковские реквизиты моей организации",
        "ACTIVE": "Y",
        "RQ_BANK_NAME": _requisities_config("BITRIX_MYCOMPANY_BANK_NAME"),
        "RQ_BIK": _requisities_config("BITRIX_MYCOMPANY_BIK"),
        "RQ_ACC_NUM": _requisities_config("BITRIX_MYCOMPANY_ACCOUNT"),
        "RQ_COR_ACC_NUM": _requisities_config("BITRIX_MYCOMPANY_COR_ACCOUNT"),
        "RQ_ACC_CURRENCY": _requisities_config("BITRIX_MYCOMPANY_ACCOUNT_CURRENCY", "RUR"),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    if not any(payload.get(k) for k in ("RQ_BANK_NAME", "RQ_BIK", "RQ_ACC_NUM", "RQ_COR_ACC_NUM")):
        return None
    return BankDetailCreate(**payload)


def _bank_detail_update_payload(*, requisite_id: int, country_id: int) -> BankDetailUpdate | None:
    dto = _bank_detail_create_payload(requisite_id=requisite_id, country_id=country_id)
    if dto is None:
        return None
    payload = dto.model_dump(exclude_none=True)
    payload.pop("ENTITY_ID", None)
    return BankDetailUpdate(**payload)


def _address_payload(*, requisite_id: int, address_type_id: int) -> AddressUpsert | None:
    street = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_STREET")
    building = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_BUILDING")
    office = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_OFFICE")
    city = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_CITY")
    postal = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_POSTAL")
    region = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_REGION")
    district = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_DISTRICT")
    country = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_COUNTRY", "Россия")
    country_code = _requisities_config("BITRIX_MYCOMPANY_ADDRESS_COUNTRY_CODE", "RU")
    address_1 = ", ".join([x for x in (street, building) if x]) or None
    payload = {
        "TYPE_ID": int(address_type_id),
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_REQUISITE,
        "ENTITY_ID": int(requisite_id),
        "ADDRESS_1": address_1,
        "ADDRESS_2": office,
        "CITY": city,
        "POSTAL_CODE": postal,
        "REGION": district,
        "PROVINCE": region,
        "COUNTRY": country,
        "COUNTRY_CODE": country_code,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    if not any(payload.get(k) for k in ("ADDRESS_1", "ADDRESS_2", "CITY", "POSTAL_CODE", "REGION", "PROVINCE", "COUNTRY", "COUNTRY_CODE")):
        return None
    return AddressUpsert(**payload)


async def _find_existing_company_id(db: AsyncSession, client: BitrixClient) -> int | None:
    mapping = await get_mapping_by_maas_id(db, MYCOMPANY_MAAS_ID, MYCOMPANY_ENTITY_TYPE)
    if mapping is not None:
        return int(mapping.bitrix_id)

    svc = CompanyService(client)
    originator_id = _requisities_config("BITRIX_MYCOMPANY_ORIGINATOR_ID", "maas")
    origin_id = _requisities_config("BITRIX_MYCOMPANY_ORIGIN_ID", "mycompany")
    if originator_id and origin_id:
        rows = await svc.list(filter={"ORIGINATOR_ID": originator_id, "ORIGIN_ID": origin_id}, order={"ID": "ASC"}, select=["ID"])
        if rows:
            company_id = _safe_int(getattr(rows[0], "ID", None))
            if company_id:
                return int(company_id)
    rows = await svc.list(filter={"IS_MY_COMPANY": "Y"}, order={"ID": "ASC"}, select=["ID"])
    if rows:
        company_id = _safe_int(getattr(rows[0], "ID", None))
        if company_id:
            return int(company_id)
    return None


async def _find_existing_requisite_id(client: BitrixClient, *, company_id: int) -> int | None:
    svc = RequisiteService(client)
    rows = await svc.list(filter={"ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY, "ENTITY_ID": int(company_id)}, order={"ID": "ASC"}, select=["ID"])
    for row in rows:
        req_id = _safe_int(getattr(row, "ID", None))
        if req_id:
            return int(req_id)
    return None


async def _find_existing_bank_detail_id(client: BitrixClient, *, requisite_id: int) -> int | None:
    svc = BankDetailService(client)
    rows = await svc.list(filter={"ENTITY_ID": int(requisite_id)}, order={"ID": "ASC"}, select=["ID"])
    for row in rows:
        bank_id = _safe_int(getattr(row, "ID", None))
        if bank_id:
            return int(bank_id)
    return None


async def sync_my_company_startup(db: AsyncSession, client: BitrixClient) -> None:
    if not _has_any_company_config():
        logger.info("Skipping Bitrix My Company startup sync: no BITRIX_MYCOMPANY_* env values configured")
        return

    country_id = _safe_int_env("BITRIX_MYCOMPANY_COUNTRY_ID", RU_COUNTRY_ID) or RU_COUNTRY_ID
    address_type_id = _safe_int_env("BITRIX_MYCOMPANY_ADDRESS_TYPE_ID", ADDRESS_TYPE_LEGAL) or ADDRESS_TYPE_LEGAL
    company_svc = CompanyService(client)
    company_id = await _find_existing_company_id(db, client)
    
    if company_id is None:
        company_id = await company_svc.add(_company_create_payload())
        logger.info("Created Bitrix My Company id=%s", company_id)
    else:
        await company_svc.update(int(company_id), _company_update_payload())
        logger.info("Updated Bitrix My Company id=%s", company_id)

    await upsert_mapping(db, MYCOMPANY_MAAS_ID, int(company_id), MYCOMPANY_ENTITY_TYPE)

    preset_id = await _resolve_company_preset_id(client, country_id=int(country_id))
    if preset_id is None:
        logger.warning("Skipping Bitrix My Company requisite sync: no requisite preset found")
        return

    requisite_svc = RequisiteService(client)
    requisite_mapping = await get_mapping_by_maas_id(db, MYCOMPANY_MAAS_ID, MYCOMPANY_REQUISITE_ENTITY_TYPE)
    requisite_id = int(requisite_mapping.bitrix_id) if requisite_mapping is not None else None
    if requisite_id is None:
        requisite_id = await _find_existing_requisite_id(client, company_id=int(company_id))
    if requisite_id is None:
        requisite_id = await requisite_svc.add(_requisite_create_payload(company_id=int(company_id), preset_id=int(preset_id)))
        logger.info("Created Bitrix My Company requisite id=%s", requisite_id)
    else:
        await requisite_svc.update(int(requisite_id), _requisite_update_payload(company_id=int(company_id), preset_id=int(preset_id)))
        logger.info("Updated Bitrix My Company requisite id=%s", requisite_id)
    await upsert_mapping(db, MYCOMPANY_MAAS_ID, int(requisite_id), MYCOMPANY_REQUISITE_ENTITY_TYPE)

    bank_detail_create = _bank_detail_create_payload(requisite_id=int(requisite_id), country_id=int(country_id))
    bank_detail_svc = BankDetailService(client)
    bank_mapping = await get_mapping_by_maas_id(db, MYCOMPANY_MAAS_ID, MYCOMPANY_BANK_DETAIL_ENTITY_TYPE)
    bank_detail_id = int(bank_mapping.bitrix_id) if bank_mapping is not None else None
    if bank_detail_id is None:
        bank_detail_id = await _find_existing_bank_detail_id(client, requisite_id=int(requisite_id))
    if bank_detail_create is None:
        if bank_detail_id is not None:
            try:
                await bank_detail_svc.delete(int(bank_detail_id))
                logger.info("Deleted Bitrix My Company bank detail id=%s because no bank fields are configured", bank_detail_id)
            except Exception as exc:
                logger.warning("Failed to delete Bitrix My Company bank detail id=%s: %s", bank_detail_id, exc)
    else:
        if bank_detail_id is None:
            bank_detail_id = await bank_detail_svc.add(bank_detail_create)
            logger.info("Created Bitrix My Company bank detail id=%s", bank_detail_id)
        else:
            await bank_detail_svc.update(int(bank_detail_id), _bank_detail_update_payload(requisite_id=int(requisite_id), country_id=int(country_id)))
            logger.info("Updated Bitrix My Company bank detail id=%s", bank_detail_id)
        await upsert_mapping(db, MYCOMPANY_MAAS_ID, int(bank_detail_id), MYCOMPANY_BANK_DETAIL_ENTITY_TYPE)

    address_svc = AddressService(client)
    address_dto = _address_payload(requisite_id=int(requisite_id), address_type_id=int(address_type_id))
    identity_filter = {"TYPE_ID": int(address_type_id), "ENTITY_TYPE_ID": CRM_OWNER_TYPE_REQUISITE, "ENTITY_ID": int(requisite_id)}
    existing = await address_svc.list(filter=identity_filter, order={"TYPE_ID": "ASC"}, select=["TYPE_ID", "ENTITY_TYPE_ID", "ENTITY_ID"])
    if address_dto is None:
        if existing:
            await address_svc.delete(AddressUpsert(TYPE_ID=int(address_type_id), ENTITY_TYPE_ID=CRM_OWNER_TYPE_REQUISITE, ENTITY_ID=int(requisite_id)))
            logger.info("Deleted Bitrix My Company address for requisite_id=%s", requisite_id)
    else:
        if existing:
            await address_svc.update(address_dto)
            logger.info("Updated Bitrix My Company address for requisite_id=%s", requisite_id)
        else:
            await address_svc.add(address_dto)
            logger.info("Created Bitrix My Company address for requisite_id=%s", requisite_id)

    await upsert_mapping(
        db,
        MYCOMPANY_MAAS_ID,
        int(company_id),
        MYCOMPANY_ENTITY_TYPE,
        buffer={
            "mycompany_requisite_id": int(requisite_id),
            "mycompany_bank_detail_id": int(bank_detail_id) if bank_detail_id is not None else None,
            "requisite_preset_id": int(preset_id),
            "requisite_country_id": int(country_id),
            "requisite_address_type_id": int(address_type_id),
        },
        merge_buffer=True,
    )
