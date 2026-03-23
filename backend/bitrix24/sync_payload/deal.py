"""Build DealCreate/DealUpdate from Kit per docs/attribute_data_mapping.md (Deal table)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.dto.deal import Deal, DealCreate, DealUpdate
from backend.bitrix24.repositories import constant_entity_repository as const_repo
from backend.models import Kit
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id, get_maas_id
from backend.bitrix24.funnel_cache import resolve_stage_name
from backend.bitrix24.sync_payload.external_lists import (
    fetch_list_values,
    resolve_location_external_id,
    resolve_location_label,
)

DEAL_ENTITY_ID = "CRM_DEAL"
UF_CRM_MAAS_ID = "UF_CRM_MAAS_ID"
UF_CRM_MANUFACTURER = "UF_CRM_MANUFACTURER"
UF_CRM_SHIPPING_COST = "UF_CRM_SHIPPING_COST"


async def _userfield_enum_label_to_bitrix_id(
    db: AsyncSession, field_name: str, label: Any
) -> int | None:
    """Resolve deal userfield enum value (label) to Bitrix enumeration ID."""
    if label is None or (isinstance(label, str) and not label.strip()):
        return None
    search_label = str(label).strip()
    userfields = await const_repo.userfield_list(db, entity_id=DEAL_ENTITY_ID, limit=500)
    uf_row = next(
        (u for u in userfields if getattr(u, "field_name", None) == field_name),
        None,
    )
    if uf_row is None:
        return None
    enum_rows = await const_repo.userfield_enum_list_by_userfield(db, uf_row.id, limit=500)
    for enum_row in enum_rows:
        if getattr(enum_row, "value", None) and str(enum_row.value).strip() == search_label:
            return await const_repo.userfield_enum_get_bitrix_id(db, enum_row.id)
    return None


async def _build_deal_userfields_from_kit(
    db: AsyncSession,
    kit: Kit,
    list_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deal userfields: UF_CRM_MAAS_ID, UF_CRM_MANUFACTURER, UF_CRM_SHIPPING_COST.
    kit.location (external ID) is resolved to label for enum matching.
    """
    userfields: dict[str, Any] = {}
    maas_id = getattr(kit, "kit_id", None)
    if maas_id is not None:
        userfields[UF_CRM_MAAS_ID] = int(maas_id)

    location = getattr(kit, "location", None)
    if location is not None:
        location_label = location
        if list_values:
            resolved_label = resolve_location_label(list_values, location)
            if resolved_label is not None:
                location_label = resolved_label
        bitrix_enum_id = await _userfield_enum_label_to_bitrix_id(
            db, UF_CRM_MANUFACTURER, location_label
        )
        userfields[UF_CRM_MANUFACTURER] = (
            bitrix_enum_id if bitrix_enum_id is not None else location_label
        )

    delivery_price = getattr(kit, "delivery_price", None)
    if delivery_price is not None:
        userfields[UF_CRM_SHIPPING_COST] = float(delivery_price)

    return userfields


async def _build_deal_base_fields(db: AsyncSession, kit: Kit) -> dict[str, Any]:
    """Build common deal fields from kit (TITLE, STAGE_ID, OPPORTUNITY, CONTACT_IDS).
    Contact ID is resolved via id mapping (kit.user_id -> Bitrix contact); contacts
    are not synced on deal change, so we rely on the mapping.
    """
    kit_id = getattr(kit, "kit_id", "")
    base: dict[str, Any] = {
        "TITLE": getattr(kit, "kit_name", None) or f"Kit {kit_id}",
        "STAGE_ID": getattr(kit, "status", None),
        "OPPORTUNITY": float(x) if (x := getattr(kit, "kit_price", None)) is not None else None,
    }
    user_id = getattr(kit, "user_id", None)
    if user_id is not None:
        bitrix_contact_id = await get_bitrix_id(db, user_id, "contact")
        if bitrix_contact_id is not None:
            base["CONTACT_IDS"] = [bitrix_contact_id]
    return base


async def kit_to_deal_create(db: AsyncSession, kit: Kit) -> DealCreate:
    """Build DealCreate from Kit; resolves kit.location (external ID) to label."""
    list_values = await fetch_list_values()
    userfields = await _build_deal_userfields_from_kit(db, kit, list_values)
    base = await _build_deal_base_fields(db, kit)
    return DealCreate(
        **base,
        userfields=userfields if userfields else None,
    )


async def kit_to_deal_update(db: AsyncSession, kit: Kit) -> DealUpdate:
    """Build DealUpdate from Kit (same fields as create)."""
    list_values = await fetch_list_values()
    userfields = await _build_deal_userfields_from_kit(db, kit, list_values)
    base = await _build_deal_base_fields(db, kit)
    return DealUpdate(
        **base,
        userfields=userfields if userfields else None,
    )


# --- Reverse: Bitrix Deal → Kit ---


async def _userfield_enum_bitrix_id_to_label(
    db: AsyncSession, field_name: str, bitrix_enum_id: Any
) -> str | None:
    """Resolve deal userfield Bitrix enum ID to enum value (label). Reverse of _userfield_enum_label_to_bitrix_id."""
    if bitrix_enum_id is None:
        return None
    try:
        enum_id = int(bitrix_enum_id)
    except (TypeError, ValueError):
        return None
    userfields = await const_repo.userfield_list(db, entity_id=DEAL_ENTITY_ID, limit=500)
    uf_row = next(
        (u for u in userfields if getattr(u, "field_name", None) == field_name),
        None,
    )
    if uf_row is None:
        return None
    maas_enum_id = await get_maas_id(db, enum_id, const_repo.ENTITY_TYPE_USERFIELD_ENUM)
    if maas_enum_id is None:
        return None
    enum_row = await const_repo.userfield_enum_get_by_id(db, maas_enum_id)
    if enum_row is None:
        return None
    value = getattr(enum_row, "value", None)
    return str(value).strip() if value is not None else None


async def _build_kit_fields_from_deal_userfields(
    db: AsyncSession,
    deal_data: dict[str, Any],
    list_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build kit fields from deal userfields: kit_id, location, delivery_price.
    Reverse of _build_deal_userfields_from_kit. UF_CRM_MANUFACTURER (enum ID) is resolved to label then to external id.
    """
    kit_fields: dict[str, Any] = {}
    maas_id = deal_data.get(UF_CRM_MAAS_ID)
    if maas_id is not None:
        kit_fields["kit_id"] = int(maas_id)

    manufacturer_enum_id = deal_data.get(UF_CRM_MANUFACTURER)
    if manufacturer_enum_id is not None:
        location_label = await _userfield_enum_bitrix_id_to_label(
            db, UF_CRM_MANUFACTURER, manufacturer_enum_id
        )
        location_label = (
            location_label if location_label is not None
            else str(manufacturer_enum_id).strip()
        )
        if list_values:
            location_external_id = resolve_location_external_id(
                list_values, location_label
            )
            kit_fields["location"] = (
                location_external_id if location_external_id is not None
                else location_label
            )
        else:
            kit_fields["location"] = location_label

    shipping_cost = deal_data.get(UF_CRM_SHIPPING_COST)
    if shipping_cost is not None:
        try:
            kit_fields["delivery_price"] = float(shipping_cost)
        except (TypeError, ValueError):
            pass

    return kit_fields


async def _build_kit_base_fields_from_deal(db: AsyncSession, deal_data: dict[str, Any]) -> dict[str, Any]:
    """Build common kit fields from deal (kit_name, status, kit_price).

    Important: deal_data['STAGE_ID'] is a technical code (e.g. NEW, C2:NEW).
    We translate it to a human-readable stage name using the local funnel cache populated on startup.
    """
    title = deal_data.get("TITLE")
    stage_id = deal_data.get("STAGE_ID")
    category_id = deal_data.get("CATEGORY_ID")
    opportunity = deal_data.get("OPPORTUNITY")

    stage_name = await resolve_stage_name(
        db,
        stage_id=str(stage_id) if stage_id is not None else None,
        category_id=int(category_id) if category_id is not None else None,
    )

    return {
        "kit_name": title,
        "status": stage_name or (str(stage_id) if stage_id is not None else None),
        "kit_price": float(opportunity) if opportunity is not None else None,
    }


async def deal_to_kit_update(
    db: AsyncSession, deal: Deal, order_ids: list[int]
) -> dict[str, Any]:
    """Build Kit update payload from Bitrix Deal and resolved order_ids.
    Reverse of kit_to_deal_*. Caller supplies order_ids (Bitrix product row → MaaS order_id mapping).
    """
    deal_data = deal.to_dict()
    list_values = await fetch_list_values()
    base_fields = await _build_kit_base_fields_from_deal(db, deal_data)
    userfield_fields = await _build_kit_fields_from_deal_userfields(
        db, deal_data, list_values
    )
    payload: dict[str, Any] = {
        **base_fields,
        **userfield_fields,
        "order_ids": order_ids,
    }
    return {k: v for k, v in payload.items() if v is not None}
