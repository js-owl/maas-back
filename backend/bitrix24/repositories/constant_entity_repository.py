"""
Repository for Bitrix24 constant-entity source-of-truth tables.
External IDs are stored only in maas_bitrix_ids_mapping; all mapping access via mapping_repository.
"""
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    BitrixCategory,
    BitrixStatus,
    BitrixUserfield,
    BitrixUserfieldEnum,
    BitrixProductProperty,
    BitrixProductPropertyEnum,
)
from backend.bitrix24.repositories.mapping_repository import (
    get_bitrix_id,
    upsert_mapping,
)

# Entity type strings for maas_bitrix_ids_mapping
ENTITY_TYPE_CATEGORY = "category"
ENTITY_TYPE_STATUS = "status"
ENTITY_TYPE_USERFIELD = "userfield"
ENTITY_TYPE_USERFIELD_ENUM = "userfield_enum"
ENTITY_TYPE_PRODUCT_PROPERTY = "product_property"
ENTITY_TYPE_PRODUCT_PROPERTY_ENUM = "product_property_enum"


# --- Category ---

async def category_create(db: AsyncSession, entity_type_id: int, name: Optional[str] = None, sort: Optional[int] = None, origin_id: Optional[str] = None, originator_id: Optional[str] = None) -> BitrixCategory:
    row = BitrixCategory(entity_type_id=entity_type_id, name=name, sort=sort, origin_id=origin_id, originator_id=originator_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def category_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixCategory]:
    result = await db.execute(select(BitrixCategory).where(BitrixCategory.id == id))
    return result.scalar_one_or_none()


async def category_list(db: AsyncSession, entity_type_id: Optional[int] = None, limit: int = 500, offset: int = 0) -> List[BitrixCategory]:
    q = select(BitrixCategory).order_by(BitrixCategory.id)
    if entity_type_id is not None:
        q = q.where(BitrixCategory.entity_type_id == entity_type_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def category_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_CATEGORY)


async def category_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_CATEGORY, buffer)


# --- Status ---

async def status_create(
    db: AsyncSession,
    entity_id: str,
    status_id: str,
    name: str,
    category_id: Optional[int] = None,
    semantics: Optional[str] = None,
    sort: Optional[int] = None,
    color: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> BitrixStatus:
    row = BitrixStatus(
        entity_id=entity_id, status_id=status_id, name=name,
        category_id=category_id, semantics=semantics, sort=sort, color=color, extra=extra
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def status_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixStatus]:
    result = await db.execute(select(BitrixStatus).where(BitrixStatus.id == id))
    return result.scalar_one_or_none()


async def status_list(
    db: AsyncSession,
    entity_id: Optional[str] = None,
    category_id: Optional[int] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[BitrixStatus]:
    q = select(BitrixStatus).order_by(BitrixStatus.id)
    if entity_id is not None:
        q = q.where(BitrixStatus.entity_id == entity_id)
    if category_id is not None:
        q = q.where(BitrixStatus.category_id == category_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def status_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_STATUS)


async def status_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_STATUS, buffer)


# --- Userfield ---

_USERFIELD_LABEL_MESSAGE_KEYS = (
    "EDIT_FORM_LABEL", "LIST_COLUMN_LABEL", "LIST_FILTER_LABEL", "ERROR_MESSAGE", "HELP_MESSAGE"
)


def _userfield_row_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map DTO-style keys to model column names for BitrixUserfield. Serialize label/message dicts to JSON."""
    key_map = {
        "ENTITY_ID": "entity_id", "FIELD_NAME": "field_name", "USER_TYPE_ID": "user_type_id",
        "XML_ID": "xml_id", "SORT": "sort", "MULTIPLE": "multiple", "MANDATORY": "mandatory",
        "SHOW_FILTER": "show_filter", "SHOW_IN_LIST": "show_in_list", "EDIT_IN_LIST": "edit_in_list",
        "IS_SEARCHABLE": "is_searchable", "LABEL": "label", "EDIT_FORM_LABEL": "edit_form_label",
        "LIST_COLUMN_LABEL": "list_column_label", "LIST_FILTER_LABEL": "list_filter_label",
        "ERROR_MESSAGE": "error_message", "HELP_MESSAGE": "help_message", "SETTINGS": "settings",
    }
    out: Dict[str, Any] = {}
    for k, v in data.items():
        col = key_map.get(k, k)
        if k in _USERFIELD_LABEL_MESSAGE_KEYS and isinstance(v, dict):
            out[col] = json.dumps(v) if v else None
        else:
            out[col] = v
    return out


async def userfield_create(db: AsyncSession, fields: Dict[str, Any]) -> BitrixUserfield:
    row = BitrixUserfield(**_userfield_row_from_dict(fields))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def userfield_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixUserfield]:
    result = await db.execute(select(BitrixUserfield).where(BitrixUserfield.id == id))
    return result.scalar_one_or_none()


async def userfield_list(
    db: AsyncSession,
    entity_id: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[BitrixUserfield]:
    q = select(BitrixUserfield).order_by(BitrixUserfield.id)
    if entity_id is not None:
        q = q.where(BitrixUserfield.entity_id == entity_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def userfield_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_USERFIELD)


async def userfield_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_USERFIELD, buffer)


# --- Userfield enumeration ---

async def userfield_enum_create(
    db: AsyncSession,
    userfield_id: int,
    sort: Optional[int] = None,
    value: Optional[str] = None,
    def_: Optional[str] = None,
    xml_id: Optional[str] = None,
) -> BitrixUserfieldEnum:
    row = BitrixUserfieldEnum(userfield_id=userfield_id, sort=sort, value=value, def_=def_, xml_id=xml_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def userfield_enum_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixUserfieldEnum]:
    result = await db.execute(select(BitrixUserfieldEnum).where(BitrixUserfieldEnum.id == id))
    return result.scalar_one_or_none()


async def userfield_enum_list_by_userfield(db: AsyncSession, userfield_id: int, limit: int = 500, offset: int = 0) -> List[BitrixUserfieldEnum]:
    q = select(BitrixUserfieldEnum).where(BitrixUserfieldEnum.userfield_id == userfield_id).order_by(BitrixUserfieldEnum.sort, BitrixUserfieldEnum.id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def userfield_enum_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_USERFIELD_ENUM)


async def userfield_enum_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_USERFIELD_ENUM, buffer)


# --- Product property ---

def _product_property_row_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    key_map = {
        "iblockId": "iblock_id", "propertyType": "property_type", "xmlId": "xml_id",
        "isRequired": "is_required", "multipleCnt": "multiple_cnt", "withDescription": "with_description",
        "rowCount": "row_count", "colCount": "col_count", "defaultValue": "default_value",
        "listType": "list_type", "linkIblockId": "link_iblock_id", "fileType": "file_type",
        "userType": "user_type", "userTypeSettings": "user_type_settings", "timestampX": "timestamp_x",
    }
    out = {}
    for k, v in data.items():
        out[key_map.get(k, k)] = v
    return out


async def product_property_create(db: AsyncSession, fields: Dict[str, Any]) -> BitrixProductProperty:
    row = BitrixProductProperty(**_product_property_row_from_dict(fields))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def product_property_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixProductProperty]:
    result = await db.execute(select(BitrixProductProperty).where(BitrixProductProperty.id == id))
    return result.scalar_one_or_none()


async def product_property_list(
    db: AsyncSession,
    iblock_id: Optional[int] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[BitrixProductProperty]:
    q = select(BitrixProductProperty).order_by(BitrixProductProperty.id)
    if iblock_id is not None:
        q = q.where(BitrixProductProperty.iblock_id == iblock_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def product_property_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_PRODUCT_PROPERTY)


async def product_property_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_PRODUCT_PROPERTY, buffer)


# --- Product property enum ---

async def product_property_enum_create(
    db: AsyncSession,
    property_id: int,
    value: str,
    xml_id: str,
    def_: Optional[str] = None,
    sort: Optional[int] = None,
) -> BitrixProductPropertyEnum:
    row = BitrixProductPropertyEnum(property_id=property_id, value=value, xml_id=xml_id, def_=def_, sort=sort)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def product_property_enum_get_by_id(db: AsyncSession, id: int) -> Optional[BitrixProductPropertyEnum]:
    result = await db.execute(select(BitrixProductPropertyEnum).where(BitrixProductPropertyEnum.id == id))
    return result.scalar_one_or_none()


async def product_property_enum_list_by_property(db: AsyncSession, property_id: int, limit: int = 500, offset: int = 0) -> List[BitrixProductPropertyEnum]:
    q = select(BitrixProductPropertyEnum).where(BitrixProductPropertyEnum.property_id == property_id).order_by(BitrixProductPropertyEnum.sort, BitrixProductPropertyEnum.id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def product_property_enum_get_bitrix_id(db: AsyncSession, maas_id: int) -> Optional[int]:
    return await get_bitrix_id(db, maas_id, ENTITY_TYPE_PRODUCT_PROPERTY_ENUM)


async def product_property_enum_set_bitrix_id(db: AsyncSession, maas_id: int, bitrix_id: int, buffer: Optional[Dict[str, Any]] = None) -> None:
    await upsert_mapping(db, maas_id, bitrix_id, ENTITY_TYPE_PRODUCT_PROPERTY_ENUM, buffer)
