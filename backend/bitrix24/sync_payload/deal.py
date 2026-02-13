"""Build DealCreate/DealUpdate from Kit per docs/attribute_data_mapping.md (Deal table)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.dto.deal import DealCreate, DealUpdate
from backend.bitrix24.repositories import constant_entity_repository as const_repo
from backend.bitrix24.sync_payload.external_lists import (
    fetch_list_values,
    resolve_location_russian_name,
)

DEAL_ENTITY_ID = "CRM_DEAL"
UF_CRM_MAAS_ID = "UF_CRM_MAAS_ID"
UF_CRM_MANUFACTURER = "UF_CRM_MANUFACTURER"
UF_CRM_SHIPPING_COST = "UF_CRM_SHIPPING_COST"


async def _resolve_deal_userfield_enum(
    db: AsyncSession, field_name: str, value: Any
) -> int | None:
    """Resolve deal userfield list value to enumeration Bitrix ID."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    str_val = str(value).strip()
    userfields = await const_repo.userfield_list(db, entity_id=DEAL_ENTITY_ID, limit=500)
    uf_row = next(
        (u for u in userfields if getattr(u, "field_name", None) == field_name),
        None,
    )
    if uf_row is None:
        return None
    enum_rows = await const_repo.userfield_enum_list_by_userfield(db, uf_row.id, limit=500)
    for enum_row in enum_rows:
        if (getattr(enum_row, "value", None) and str(enum_row.value).strip() == str_val) or (
            getattr(enum_row, "xml_id", None) and str(enum_row.xml_id).strip() == str_val
        ):
            return await const_repo.userfield_enum_get_bitrix_id(db, enum_row.id)
    return None


async def _deal_userfields_from_kit(
    db: AsyncSession,
    kit: Any,
    list_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deal userfields: UF_CRM_MAAS_ID, UF_CRM_MANUFACTURER, UF_CRM_SHIPPING_COST.
    kit.location (external ID) is resolved to russian_name for enum matching.
    """
    userfields: dict[str, Any] = {}
    maas_id = getattr(kit, "kit_id", None)
    if maas_id is not None:
        userfields[UF_CRM_MAAS_ID] = int(maas_id)

    location = getattr(kit, "location", None)
    if location is not None:
        value_for_enum = location
        if list_values:
            resolved = resolve_location_russian_name(list_values, location)
            if resolved is not None:
                value_for_enum = resolved
        enum_id = await _resolve_deal_userfield_enum(db, UF_CRM_MANUFACTURER, value_for_enum)
        userfields[UF_CRM_MANUFACTURER] = enum_id if enum_id is not None else value_for_enum

    delivery = getattr(kit, "delivery_price", None)
    if delivery is not None:
        userfields[UF_CRM_SHIPPING_COST] = float(delivery)

    return userfields


def _deal_base_fields(kit: Any) -> dict:
    """Common deal fields from kit (TITLE, STAGE_ID, OPPORTUNITY)."""
    return {
        "TITLE": getattr(kit, "kit_name", None) or f"Kit {getattr(kit, 'kit_id', '')}",
        "STAGE_ID": getattr(kit, "status", None),
        "OPPORTUNITY": float(x) if (x := getattr(kit, "kit_price", None)) is not None else None,
    }


async def kit_to_deal_create(db: AsyncSession, kit: Any) -> DealCreate:
    """Build DealCreate from Kit; resolves kit.location (external ID) to russian_name."""
    list_values = await fetch_list_values()
    userfields = await _deal_userfields_from_kit(db, kit, list_values)
    return DealCreate(
        **_deal_base_fields(kit),
        userfields=userfields if userfields else None,
    )


async def kit_to_deal_update(db: AsyncSession, kit: Any) -> DealUpdate:
    """Build DealUpdate from Kit (same fields as create)."""
    list_values = await fetch_list_values()
    userfields = await _deal_userfields_from_kit(db, kit, list_values)
    return DealUpdate(
        **_deal_base_fields(kit),
        userfields=userfields if userfields else None,
    )
