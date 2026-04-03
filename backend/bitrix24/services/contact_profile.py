"""Sync Bitrix contact requisites/addresses for users."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto.address import AddressUpsert
from backend.bitrix24.exceptions import BitrixAPIError
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id, upsert_mapping
from backend.bitrix24.services.address import AddressService
from backend.bitrix24.services.requisite import RequisiteService
from backend.bitrix24.sync_payload.requisite import (
    ADDRESS_TYPE_FACT,
    CRM_OWNER_TYPE_CONTACT,
    CRM_OWNER_TYPE_REQUISITE,
    RU_COUNTRY_ID,
    has_address_payload,
    user_to_contact_address,
    user_to_contact_requisite_create,
    user_to_contact_requisite_update,
)
from backend.models import User
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REQUISITE_MAPPING_ENTITY_TYPE = "contact_requisite"

_ENV_PRESET_ID = "BITRIX_CONTACT_REQUISITE_PRESET_ID"
_ENV_COUNTRY_ID = "BITRIX_CONTACT_REQUISITE_COUNTRY_ID"
_ENV_ADDRESS_TYPE_ID = "BITRIX_CONTACT_REQUISITE_ADDRESS_TYPE_ID"


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
    return _safe_int_env(_ENV_ADDRESS_TYPE_ID, ADDRESS_TYPE_FACT) or ADDRESS_TYPE_FACT


async def _resolve_contact_preset_id(client: BitrixClient, *, country_id: int) -> int | None:
    preset_id = _safe_int_env(_ENV_PRESET_ID)
    if preset_id:
        return preset_id

    candidates: list[dict[str, Any]] = []
    for filter_payload in (
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_CONTACT, "COUNTRY_ID": country_id},
        {"ENTITY_TYPE_ID": CRM_OWNER_TYPE_CONTACT},
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
            logger.warning("Failed to resolve contact requisite preset list with filter=%s: %s", filter_payload, exc)
            continue

        if isinstance(result, list) and result:
            candidates = result
            break

    filtered = [
        item
        for item in candidates
        if str(item.get("ENTITY_TYPE_ID")) == str(CRM_OWNER_TYPE_CONTACT)
        and (item.get("COUNTRY_ID") is None or str(item.get("COUNTRY_ID")) == str(country_id))
    ]
    if filtered:
        return int(filtered[0]["ID"])
    if candidates:
        return int(candidates[0]["ID"])
    return None


async def _find_requisite_id(client: BitrixClient, *, contact_id: int) -> int | None:
    svc = RequisiteService(client)
    result = await svc.list(
        filter={
            "ENTITY_TYPE_ID": CRM_OWNER_TYPE_CONTACT,
            "ENTITY_ID": int(contact_id),
        },
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
    contact_id: int,
    preset_id: int,
) -> int:
    requisite_svc = RequisiteService(client)
    requisite_id = await get_bitrix_id(db, user.id, REQUISITE_MAPPING_ENTITY_TYPE)
    if requisite_id is None:
        requisite_id = await _find_requisite_id(client, contact_id=contact_id)

    if requisite_id is None:
        dto = user_to_contact_requisite_create(user, contact_id=contact_id, preset_id=preset_id)
        requisite_id = await requisite_svc.add(dto)
        logger.info("Created Bitrix contact requisite for MaaS user_id=%s contact_id=%s requisite_id=%s", user.id, contact_id, requisite_id)
    else:
        dto = user_to_contact_requisite_update(user, contact_id=contact_id, preset_id=preset_id)
        try:
            await requisite_svc.update(int(requisite_id), dto)
            logger.info("Updated Bitrix contact requisite for MaaS user_id=%s contact_id=%s requisite_id=%s", user.id, contact_id, requisite_id)
        except Exception as exc:
            if not _is_remote_missing_error(exc):
                raise
            dto_create = user_to_contact_requisite_create(user, contact_id=contact_id, preset_id=preset_id)
            requisite_id = await requisite_svc.add(dto_create)
            logger.info("Re-created Bitrix contact requisite for MaaS user_id=%s contact_id=%s requisite_id=%s", user.id, contact_id, requisite_id)

    await upsert_mapping(db, user.id, int(requisite_id), REQUISITE_MAPPING_ENTITY_TYPE)
    return int(requisite_id)


async def _upsert_contact_address(
    client: BitrixClient,
    *,
    user: User,
    requisite_id: int,
    address_type_id: int,
) -> None:
    address_svc = AddressService(client)
    dto = user_to_contact_address(user, requisite_id=requisite_id, type_id=address_type_id)
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
                logger.info("Deleted Bitrix contact address for requisite_id=%s", requisite_id)
            except Exception as exc:
                logger.warning("Failed to delete contact address for requisite_id=%s: %s", requisite_id, exc)
        return

    if existing:
        await address_svc.update(dto)
        logger.info("Updated Bitrix contact address for requisite_id=%s", requisite_id)
    else:
        await address_svc.add(dto)
        logger.info("Created Bitrix contact address for requisite_id=%s", requisite_id)


async def sync_contact_profile(
    db: AsyncSession,
    client: BitrixClient,
    *,
    user: User,
    contact_id: int,
) -> None:
    """Sync requisite-backed address for a Bitrix contact created from MaaS user."""
    if not has_address_payload(user):
        requisite_id = await get_bitrix_id(db, user.id, REQUISITE_MAPPING_ENTITY_TYPE)
        if requisite_id is None:
            requisite_id = await _find_requisite_id(client, contact_id=int(contact_id))
            if requisite_id is not None:
                await upsert_mapping(db, user.id, int(requisite_id), REQUISITE_MAPPING_ENTITY_TYPE)
        if requisite_id is not None:
            address_type_id = await _resolve_address_type_id()
            await _upsert_contact_address(client, user=user, requisite_id=int(requisite_id), address_type_id=int(address_type_id))
        return

    country_id = await _resolve_country_id()
    address_type_id = await _resolve_address_type_id()
    preset_id = await _resolve_contact_preset_id(client, country_id=country_id)
    if preset_id is None:
        logger.error(
            "Bitrix requisite preset for contact was not found. Set %s explicitly or create a contact preset on the portal.",
            _ENV_PRESET_ID,
        )
        return

    requisite_id = await _upsert_requisite(
        db,
        client,
        user=user,
        contact_id=int(contact_id),
        preset_id=int(preset_id),
    )
    await _upsert_contact_address(
        client,
        user=user,
        requisite_id=int(requisite_id),
        address_type_id=int(address_type_id),
    )
