"""Sync Bitrix company requisites/bank details/addresses for legal users."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto.address import AddressUpsert
from backend.bitrix24.exceptions import BitrixAPIError
from backend.bitrix24.repositories.mapping_repository import (
    delete_mappings_by_entity,
    get_bitrix_id,
    upsert_mapping,
)
from backend.bitrix24.services.address import AddressService
from backend.bitrix24.services.bank_detail import BankDetailService
from backend.bitrix24.services.contact import ContactService
from backend.bitrix24.services.contact_profile import sync_contact_profile
from backend.bitrix24.services.requisite import RequisiteService
from backend.bitrix24.sync_payload.contact import (
    has_company_contact_payload,
    user_to_company_contact_create,
    user_to_company_contact_update,
)
from backend.bitrix24.sync_payload.requisite import (
    ADDRESS_TYPE_LEGAL,
    CRM_OWNER_TYPE_COMPANY,
    CRM_OWNER_TYPE_REQUISITE,
    RU_COUNTRY_ID,
    user_to_bank_detail_create,
    user_to_bank_detail_update,
    user_to_legal_address,
    user_to_requisite_create,
    user_to_requisite_update,
)
from backend.models import User
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REQUISTE_MAPPING_ENTITY_TYPE = "company_requisite"
BANK_DETAIL_MAPPING_ENTITY_TYPE = "company_bank_detail"
CONTACT_MAPPING_ENTITY_TYPE = "contact"
_COMPANY_MAPPING_ENTITY_TYPE = "company"

_ENV_PRESET_ID = "BITRIX_COMPANY_REQUISITE_PRESET_ID"
_ENV_COUNTRY_ID = "BITRIX_COMPANY_REQUISITE_COUNTRY_ID"
_ENV_ADDRESS_TYPE_ID = "BITRIX_COMPANY_REQUISITE_ADDRESS_TYPE_ID"


def _safe_int_env(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid integer in %s=%r; using default=%r", name, raw, default)
        return default


def _is_remote_missing_error(exc: Exception) -> bool:
    if not isinstance(exc, BitrixAPIError):
        return False
    hay = f"{exc.code} {exc.description}".lower()
    return exc.status_code == 404 or "not found" in hay or "не найден" in hay or "could not find" in hay


async def _resolve_country_id() -> int:
    return _safe_int_env(_ENV_COUNTRY_ID, RU_COUNTRY_ID) or RU_COUNTRY_ID


async def _resolve_address_type_id() -> int:
    return _safe_int_env(_ENV_ADDRESS_TYPE_ID, ADDRESS_TYPE_LEGAL) or ADDRESS_TYPE_LEGAL


async def _resolve_company_preset_id(client: BitrixClient, *, country_id: int) -> int | None:
    preset_id = _safe_int_env(_ENV_PRESET_ID)
    if preset_id:
        return preset_id

    candidates: list[dict[str, Any]] = []
    for filter_payload in (
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY, "COUNTRY_ID": country_id},
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY},
        None,
    ):
        try:
            result = await client.call(
                "crm.requisite.preset.list",
                {
                    "filter": filter_payload,
                    "order": {"SORT": "ASC", "ID": "ASC"},
                    "select": ["ID", "ENTITY_TYPE_ID", "COUNTRY_ID", "SORT", "NAME", "ACTIVE"],
                },
            )
        except Exception as exc:
            logger.warning("Failed to resolve requisite preset list with filter=%s: %s", filter_payload, exc)
            continue

        if isinstance(result, list) and result:
            candidates = result
            break

    filtered = [
        item
        for item in candidates
        if str(item.get("ENTITY_TYPE_ID")) == str(CRM_OWNER_TYPE_COMPANY)
        and (item.get("COUNTRY_ID") is None or str(item.get("COUNTRY_ID")) == str(country_id))
    ]
    if filtered:
        return int(filtered[0]["ID"])
    if candidates:
        return int(candidates[0]["ID"])
    return None


async def _find_requisite_id(client: BitrixClient, *, company_id: int) -> int | None:
    svc = RequisiteService(client)
    result = await svc.list(
        filter={
            "ENTITY_TYPE_ID": CRM_OWNER_TYPE_COMPANY,
            "ENTITY_ID": int(company_id),
        },
        order={"ID": "ASC"},
        select=["ID"],
    )
    if result:
        return int(result[0].ID)
    return None


async def _find_bank_detail_id(client: BitrixClient, *, requisite_id: int) -> int | None:
    svc = BankDetailService(client)
    result = await svc.list(
        filter={"ENTITY_ID": int(requisite_id)},
        order={"ID": "ASC"},
        select=["ID"],
    )
    if result:
        return int(result[0].ID)
    return None


async def _find_contact_id(client: BitrixClient, *, origin_id: str) -> int | None:
    svc = ContactService(client)
    result = await svc.list(
        filter={"ORIGIN_ID": origin_id},
        order={"ID": "ASC"},
        select=["ID"],
    )
    if result:
        return int(result[0].ID)
    return None


async def _upsert_requisite(
    db: AsyncSession,
    client: BitrixClient,
    *,
    user: User,
    company_id: int,
    preset_id: int,
) -> int:
    requisite_svc = RequisiteService(client)
    requisite_id = await get_bitrix_id(db, user.id, REQUISTE_MAPPING_ENTITY_TYPE)
    if requisite_id is None:
        requisite_id = await _find_requisite_id(client, company_id=company_id)

    if requisite_id is None:
        dto = user_to_requisite_create(user, company_id=company_id, preset_id=preset_id)
        requisite_id = await requisite_svc.add(dto)
        logger.info("Created Bitrix requisite for MaaS user_id=%s company_id=%s requisite_id=%s", user.id, company_id, requisite_id)
    else:
        dto = user_to_requisite_update(user, company_id=company_id, preset_id=preset_id)
        try:
            await requisite_svc.update(int(requisite_id), dto)
            logger.info("Updated Bitrix requisite for MaaS user_id=%s company_id=%s requisite_id=%s", user.id, company_id, requisite_id)
        except Exception as exc:
            if not _is_remote_missing_error(exc):
                raise
            dto_create = user_to_requisite_create(user, company_id=company_id, preset_id=preset_id)
            requisite_id = await requisite_svc.add(dto_create)
            logger.info("Re-created Bitrix requisite for MaaS user_id=%s company_id=%s requisite_id=%s", user.id, company_id, requisite_id)

    await upsert_mapping(db, user.id, int(requisite_id), REQUISTE_MAPPING_ENTITY_TYPE)
    return int(requisite_id)


async def _upsert_bank_detail(
    db: AsyncSession,
    client: BitrixClient,
    *,
    user: User,
    requisite_id: int,
    country_id: int,
) -> int | None:
    bank_svc = BankDetailService(client)
    bank_detail_id = await get_bitrix_id(db, user.id, BANK_DETAIL_MAPPING_ENTITY_TYPE)
    if bank_detail_id is None:
        bank_detail_id = await _find_bank_detail_id(client, requisite_id=requisite_id)

    create_dto = user_to_bank_detail_create(user, requisite_id=requisite_id, country_id=country_id)
    update_dto = user_to_bank_detail_update(user, requisite_id=requisite_id, country_id=country_id)

    if create_dto is None or update_dto is None:
        if bank_detail_id is not None:
            try:
                await bank_svc.delete(int(bank_detail_id))
                logger.info(
                    "Deleted Bitrix bank detail for MaaS user_id=%s requisite_id=%s bank_detail_id=%s because no local bank data remains",
                    user.id,
                    requisite_id,
                    bank_detail_id,
                )
            except Exception as exc:
                logger.warning("Failed to delete bank detail %s for MaaS user_id=%s: %s", bank_detail_id, user.id, exc)
            await delete_mappings_by_entity(db, user.id, BANK_DETAIL_MAPPING_ENTITY_TYPE)
        return None

    if bank_detail_id is None:
        bank_detail_id = await bank_svc.add(create_dto)
        logger.info("Created Bitrix bank detail for MaaS user_id=%s requisite_id=%s bank_detail_id=%s", user.id, requisite_id, bank_detail_id)
    else:
        try:
            await bank_svc.update(int(bank_detail_id), update_dto)
            logger.info("Updated Bitrix bank detail for MaaS user_id=%s requisite_id=%s bank_detail_id=%s", user.id, requisite_id, bank_detail_id)
        except Exception as exc:
            if not _is_remote_missing_error(exc):
                raise
            bank_detail_id = await bank_svc.add(create_dto)
            logger.info("Re-created Bitrix bank detail for MaaS user_id=%s requisite_id=%s bank_detail_id=%s", user.id, requisite_id, bank_detail_id)

    await upsert_mapping(db, user.id, int(bank_detail_id), BANK_DETAIL_MAPPING_ENTITY_TYPE)
    return int(bank_detail_id)


async def _upsert_legal_address(
    client: BitrixClient,
    *,
    user: User,
    requisite_id: int,
    address_type_id: int,
) -> None:
    address_svc = AddressService(client)
    dto = user_to_legal_address(user, requisite_id=requisite_id, type_id=address_type_id)
    identity_filter = {
        "TYPE_ID": int(address_type_id),
        "ENTITY_TYPE_ID": CRM_OWNER_TYPE_REQUISITE,
        "ENTITY_ID": int(requisite_id),
    }
    existing = await address_svc.list(filter=identity_filter, order={"TYPE_ID": "ASC"}, select=["TYPE_ID", "ENTITY_TYPE_ID", "ENTITY_ID"])

    if dto is None:
        if existing:
            try:
                await address_svc.delete(
                    AddressUpsert(
                        TYPE_ID=int(address_type_id),
                        ENTITY_TYPE_ID=CRM_OWNER_TYPE_REQUISITE,
                        ENTITY_ID=int(requisite_id),
                    )
                )
                logger.info("Deleted Bitrix legal address for requisite_id=%s", requisite_id)
            except Exception as exc:
                logger.warning("Failed to delete legal address for requisite_id=%s: %s", requisite_id, exc)
        return

    if existing:
        await address_svc.update(dto)
        logger.info("Updated Bitrix legal address for requisite_id=%s", requisite_id)
    else:
        await address_svc.add(dto)
        logger.info("Created Bitrix legal address for requisite_id=%s", requisite_id)


async def _upsert_company_contact(
    db: AsyncSession,
    client: BitrixClient,
    *,
    user: User,
    company_id: int,
) -> int | None:
    if not has_company_contact_payload(user):
        return None

    contact_svc = ContactService(client)
    contact_id = await get_bitrix_id(db, user.id, CONTACT_MAPPING_ENTITY_TYPE)
    if contact_id is None:
        contact_id = await _find_contact_id(client, origin_id=str(user.id))

    if contact_id is None:
        dto = user_to_company_contact_create(user, company_id=company_id)
        contact_id = await contact_svc.add(dto)
        logger.info("Created Bitrix linked contact for MaaS legal user_id=%s contact_id=%s company_id=%s", user.id, contact_id, company_id)
    else:
        dto = user_to_company_contact_update(user, company_id=company_id)
        try:
            await contact_svc.update(int(contact_id), dto)
            logger.info("Updated Bitrix linked contact for MaaS legal user_id=%s contact_id=%s company_id=%s", user.id, contact_id, company_id)
        except Exception as exc:
            if not _is_remote_missing_error(exc):
                raise
            dto_create = user_to_company_contact_create(user, company_id=company_id)
            contact_id = await contact_svc.add(dto_create)
            logger.info("Re-created Bitrix linked contact for MaaS legal user_id=%s contact_id=%s company_id=%s", user.id, contact_id, company_id)

    await upsert_mapping(db, user.id, int(contact_id), CONTACT_MAPPING_ENTITY_TYPE)
    return int(contact_id)


async def sync_company_legal_profile(
    db: AsyncSession,
    client: BitrixClient,
    *,
    user: User,
    company_id: int,
) -> None:
    """Sync requisite, bank detail, legal address and optional contact for a MaaS legal user."""
    if getattr(user, "user_type", None) != "legal":
        return

    country_id = await _resolve_country_id()
    address_type_id = await _resolve_address_type_id()
    preset_id = await _resolve_company_preset_id(client, country_id=country_id)
    if preset_id is None:
        logger.error(
            "Bitrix requisite preset for company was not found. Set %s explicitly or create a company preset on the portal.",
            _ENV_PRESET_ID,
        )
        return

    requisite_id = await _upsert_requisite(
        db,
        client,
        user=user,
        company_id=company_id,
        preset_id=int(preset_id),
    )
    bank_detail_id = await _upsert_bank_detail(
        db,
        client,
        user=user,
        requisite_id=int(requisite_id),
        country_id=int(country_id),
    )
    await _upsert_legal_address(
        client,
        user=user,
        requisite_id=int(requisite_id),
        address_type_id=int(address_type_id),
    )
    contact_id = await _upsert_company_contact(
        db,
        client,
        user=user,
        company_id=int(company_id),
    )
    if contact_id is not None:
        await sync_contact_profile(
            db,
            client,
            user=user,
            contact_id=int(contact_id),
        )

    await upsert_mapping(
        db,
        user.id,
        int(company_id),
        _COMPANY_MAPPING_ENTITY_TYPE,
        buffer={
            "client_requisite_id": int(requisite_id),
            "client_bank_detail_id": int(bank_detail_id) if bank_detail_id is not None else None,
            "client_contact_id": int(contact_id) if contact_id is not None else None,
            "requisite_preset_id": int(preset_id),
            "requisite_country_id": int(country_id),
            "requisite_address_type_id": int(address_type_id),
        },
        merge_buffer=True,
    )
