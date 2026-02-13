"""
Startup sync: reconcile local constant-entity rows with Bitrix24.
Match by name (category, status) or XML ID (userfield, product_property, product_property_enum).
If found in B24 → upsert mapping; if not → create in B24 and store mapping.
Userfield enumerations are resolved after userfield create/update via userfield.get LIST.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto.category import CategoryCreate
from backend.bitrix24.dto.status import StatusCreate
from backend.bitrix24.dto.userfield import UserfieldCreate
from backend.bitrix24.dto.product_property import ProductPropertyCreate
from backend.bitrix24.dto.product_property_enum import ProductPropertyEnumCreate
from backend.bitrix24.services.category import CategoryService
from backend.bitrix24.services.status import StatusService
from backend.bitrix24.services.userfield import UserfieldService
from backend.bitrix24.services.product_property import ProductPropertyService
from backend.bitrix24.services.product_property_enum import ProductPropertyEnumService
from backend.bitrix24.repositories import constant_entity_repository as repo

logger = logging.getLogger(__name__)

# Entity name for userfield service: ENTITY_ID has prefix CRM_ (e.g. CRM_DEAL, CRM_LEAD, CRM_CONTACT)
def _entity_name_from_entity_id(entity_id: str) -> str:
    name = entity_id.replace("CRM_", "", 1).strip().lower()
    return name if name in ("deal", "lead", "contact") else name


async def _sync_categories(db: AsyncSession, client: BitrixClient) -> None:
    """Sync bitrix_category rows: one list() per entity_type_id, match by name in memory; create only when missing."""
    category_service = CategoryService(client)
    rows = await repo.category_list(db, limit=2000)
    by_entity_type: Dict[int, List[Any]] = defaultdict(list)
    for row in rows:
        by_entity_type[row.entity_type_id].append(row)
    for entity_type_id, group in by_entity_type.items():
        try:
            existing = await category_service.list(entity_type_id)
            name_to_category = {category.name: category for category in existing if getattr(category, "id", None) is not None}
            for row in group:
                try:
                    match = name_to_category.get(row.name)
                    if match:
                        bitrix_id = int(match.id)
                        await repo.category_set_bitrix_id(db, row.id, bitrix_id)
                        logger.debug("Category maas_id=%s matched B24 id=%s", row.id, bitrix_id)
                    else:
                        fields = CategoryCreate(entityTypeId=row.entity_type_id, name=row.name, sort=row.sort, originId=row.origin_id, originatorId=row.originator_id)
                        bitrix_id = await category_service.add(row.entity_type_id, fields)
                        await repo.category_set_bitrix_id(db, row.id, bitrix_id)
                        logger.info("Category maas_id=%s created in B24 id=%s", row.id, bitrix_id)
                except Exception as error:
                    logger.warning("Startup sync category id=%s failed: %s", row.id, error)
        except Exception as error:
            logger.warning("Startup sync categories entity_type_id=%s failed: %s", entity_type_id, error)


async def _sync_statuses(db: AsyncSession, client: BitrixClient) -> None:
    """Sync bitrix_status rows: one list() per ENTITY_ID, match by STATUS_ID in memory; create only when missing."""
    status_service = StatusService(client)
    rows = await repo.status_list(db, limit=2000)
    by_entity_id: Dict[str, List[Any]] = defaultdict(list)
    for row in rows:
        by_entity_id[row.entity_id].append(row)
    for entity_id, group in by_entity_id.items():
        try:
            existing = await status_service.list({"ENTITY_ID": entity_id})
            status_id_to_status = {getattr(status, "STATUS_ID"): status for status in existing if getattr(status, "ID", None) is not None and getattr(status, "STATUS_ID", None) is not None}
            for row in group:
                try:
                    status_id = row.status_id
                    match = status_id_to_status.get(status_id)
                    if match:
                        bitrix_id = int(match.ID)
                        await repo.status_set_bitrix_id(db, row.id, bitrix_id)
                        logger.debug("Status maas_id=%s matched B24 id=%s", row.id, bitrix_id)
                    else:
                        fields = StatusCreate(
                            ENTITY_ID=entity_id,
                            STATUS_ID=status_id,
                            NAME=row.name,
                            CATEGORY_ID=row.category_id,
                            SEMANTICS=row.semantics,
                            SORT=row.sort,
                            COLOR=row.color,
                            EXTRA=row.extra,
                        )
                        bitrix_id = await status_service.add(fields)
                        await repo.status_set_bitrix_id(db, row.id, bitrix_id)
                        logger.info("Status maas_id=%s created in B24 id=%s", row.id, bitrix_id)
                except Exception as error:
                    logger.warning("Startup sync status id=%s failed: %s", row.id, error)
        except Exception as error:
            logger.warning("Startup sync statuses ENTITY_ID=%s failed: %s", entity_id, error)


def _parse_label_message(val: Any) -> Optional[Dict[str, str]]:
    """Parse label/message from DB: JSON string -> dict[str, str]; None or invalid -> None."""
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _userfield_to_create_payload(row: Any) -> Dict[str, Any]:
    """Build UserfieldCreate-like payload from BitrixUserfield row (no LIST - caller adds from enums)."""
    return {
        "ENTITY_ID": row.entity_id,
        "FIELD_NAME": row.field_name,
        "USER_TYPE_ID": row.user_type_id,
        "XML_ID": row.xml_id,
        "SORT": row.sort,
        "MULTIPLE": row.multiple,
        "MANDATORY": row.mandatory,
        "SHOW_FILTER": row.show_filter,
        "SHOW_IN_LIST": row.show_in_list,
        "EDIT_IN_LIST": row.edit_in_list,
        "IS_SEARCHABLE": row.is_searchable,
        "LABEL": row.label,
        "EDIT_FORM_LABEL": _parse_label_message(row.edit_form_label),
        "LIST_COLUMN_LABEL": _parse_label_message(row.list_column_label),
        "LIST_FILTER_LABEL": _parse_label_message(row.list_filter_label),
        "ERROR_MESSAGE": _parse_label_message(row.error_message),
        "HELP_MESSAGE": _parse_label_message(row.help_message),
        "SETTINGS": row.settings,
    }


async def _sync_userfields(db: AsyncSession, client: BitrixClient) -> None:
    """Sync bitrix_userfield rows: one list() per entity (deal/lead/contact), match by XML_ID in memory; create when missing."""
    rows = await repo.userfield_list(db, limit=2000)
    by_entity: Dict[str, List[Any]] = defaultdict(list)
    for row in rows:
        by_entity[_entity_name_from_entity_id(row.entity_id)].append(row)
    for entity_name, group in by_entity.items():
        userfield_service = UserfieldService(client, entity_name)
        try:
            existing = await userfield_service.list()
            xml_id_to_userfield = {}
            for userfield in existing:
                userfield_xml_id = getattr(userfield, "XML_ID", None)
                if userfield_xml_id is not None and (getattr(userfield, "ID", None) or getattr(userfield, "id", None)) is not None:
                    xml_id_to_userfield[userfield_xml_id] = userfield
        except Exception as error:
            logger.warning("Startup sync userfield list entity=%s failed: %s", entity_name, error)
            xml_id_to_userfield = {}
        for row in group:
            try:
                xml_id = row.xml_id
                match = xml_id_to_userfield.get(xml_id)
                if match:
                    bitrix_id = int(getattr(match, "ID", None) or getattr(match, "id", None))
                    await repo.userfield_set_bitrix_id(db, row.id, bitrix_id)
                    if row.user_type_id and row.user_type_id.lower() in ("enumeration", "list"):
                        await _persist_userfield_enum_ids(db, userfield_service, bitrix_id, row.id)
                    logger.debug("Userfield maas_id=%s matched B24 id=%s", row.id, bitrix_id)
                    continue
                payload = _userfield_to_create_payload(row)
                if row.user_type_id and row.user_type_id.lower() in ("enumeration", "list"):
                    enumeration_rows = await repo.userfield_enum_list_by_userfield(db, row.id, limit=500)
                    payload["LIST"] = [{"VALUE": enum_item.value, "DEF": enum_item.def_, "SORT": enum_item.sort, "XML_ID": enum_item.xml_id} for enum_item in enumeration_rows]
                fields = UserfieldCreate(**payload)
                bitrix_id = await userfield_service.add(fields)
                await repo.userfield_set_bitrix_id(db, row.id, bitrix_id)
                xml_id_to_userfield[xml_id] = type("_", (), {"ID": bitrix_id, "id": bitrix_id})()
                if row.user_type_id and row.user_type_id.lower() in ("enumeration", "list"):
                    await _persist_userfield_enum_ids(db, userfield_service, bitrix_id, row.id)
                logger.info("Userfield maas_id=%s created in B24 id=%s", row.id, bitrix_id)
            except Exception as error:
                logger.warning("Startup sync userfield id=%s failed: %s", row.id, error)


async def _persist_userfield_enum_ids(db: AsyncSession, userfield_service: UserfieldService, bitrix_userfield_id: int, local_userfield_id: int) -> None:
    """Call userfield.get(bitrix_userfield_id), correlate LIST to local enum rows by VALUE, persist each enum Bitrix ID."""
    try:
        userfield_response = await userfield_service.get(str(bitrix_userfield_id))
        list_items = getattr(userfield_response, "LIST", None) or []
        local_enums = await repo.userfield_enum_list_by_userfield(db, local_userfield_id, limit=500)
        for local_enum in local_enums:
            value = local_enum.value
            match = next((item for item in list_items if item.get("VALUE") == value), None)
            if match:
                bitrix_enum_id = match.get("ID") or match.get("id")
                await repo.userfield_enum_set_bitrix_id(db, local_enum.id, int(bitrix_enum_id))
    except Exception as error:
        logger.warning("Persist userfield enum IDs for userfield_id=%s failed: %s", local_userfield_id, error)


def _product_property_to_create(row: Any) -> ProductPropertyCreate:
    return ProductPropertyCreate(
        iblockId=row.iblock_id,
        name=row.name,
        propertyType=row.property_type,
        code=row.code,
        xmlId=row.xml_id,
        active=row.active,
        sort=row.sort,
        isRequired=row.is_required,
        multiple=row.multiple,
        multipleCnt=row.multiple_cnt,
        withDescription=row.with_description,
        hint=row.hint,
        rowCount=row.row_count,
        colCount=row.col_count,
        searchable=row.searchable,
        filtrable=row.filtrable,
        defaultValue=row.default_value,
        listType=row.list_type,
        linkIblockId=row.link_iblock_id,
        fileType=row.file_type,
        userType=row.user_type,
        userTypeSettings=row.user_type_settings,
    )


async def _sync_product_properties(db: AsyncSession, client: BitrixClient) -> None:
    """Sync bitrix_product_property: one list() call, match by xmlId in memory; create when missing."""
    product_property_service = ProductPropertyService(client)
    rows = await repo.product_property_list(db, limit=2000)
    try:
        existing = await product_property_service.list()
        xml_id_to_property = {getattr(property_item, "xmlId"): property_item for property_item in existing if getattr(property_item, "id", None) is not None}
    except Exception as error:
        logger.warning("Startup sync product_property list failed: %s", error)
        xml_id_to_property = {}
    for row in rows:
        try:
            xml_id = row.xml_id
            match = xml_id_to_property.get(xml_id)
            if match:
                bitrix_id = int(match.id)
                await repo.product_property_set_bitrix_id(db, row.id, bitrix_id)
                logger.debug("Product property maas_id=%s matched B24 id=%s", row.id, bitrix_id)
            else:
                fields = _product_property_to_create(row)
                bitrix_id = await product_property_service.add(fields)
                await repo.product_property_set_bitrix_id(db, row.id, bitrix_id)
                xml_id_to_property[xml_id] = type("_", (), {"id": bitrix_id})()
                logger.info("Product property maas_id=%s created in B24 id=%s", row.id, bitrix_id)
        except Exception as error:
            logger.warning("Startup sync product_property id=%s failed: %s", row.id, error)


async def _sync_product_property_enums(db: AsyncSession, client: BitrixClient) -> None:
    """Sync bitrix_product_property_enum: one list(propertyId) per property, match by xmlId in memory; create when missing."""
    product_property_enum_service = ProductPropertyEnumService(client)
    prop_rows = await repo.product_property_list(db, limit=2000)
    for prop_row in prop_rows:
        bitrix_property_id = await repo.product_property_get_bitrix_id(db, prop_row.id)
        enum_rows = await repo.product_property_enum_list_by_property(db, prop_row.id, limit=500)
        try:
            existing = await product_property_enum_service.list(filter={"propertyId": bitrix_property_id})
            xml_id_to_enum = {getattr(enum_item, "xmlId"): enum_item for enum_item in existing if getattr(enum_item, "id", None) is not None}
        except Exception as error:
            logger.warning("Startup sync product_property_enum list property_id=%s failed: %s", prop_row.id, error)
            xml_id_to_enum = {}
        for enum_row in enum_rows:
            try:
                xml_id = enum_row.xml_id
                match = xml_id_to_enum.get(xml_id)
                if match:
                    bitrix_id = int(match.id)
                    await repo.product_property_enum_set_bitrix_id(db, enum_row.id, bitrix_id)
                    logger.debug("Product property enum maas_id=%s matched B24 id=%s", enum_row.id, bitrix_id)
                else:
                    fields = ProductPropertyEnumCreate(
                        propertyId=bitrix_property_id,
                        value=enum_row.value,
                        xmlId=enum_row.xml_id,
                        def_=enum_row.def_,
                        sort=enum_row.sort,
                    )
                    bitrix_id = await product_property_enum_service.add(fields)
                    await repo.product_property_enum_set_bitrix_id(db, enum_row.id, bitrix_id)
                    xml_id_to_enum[xml_id] = type("_", (), {"id": bitrix_id})()
                    logger.info("Product property enum maas_id=%s created in B24 id=%s", enum_row.id, bitrix_id)
            except Exception as error:
                logger.warning("Startup sync product_property_enum id=%s failed: %s", enum_row.id, error)


async def run_constant_entity_startup_sync(db: AsyncSession, client: BitrixClient) -> None:
    """
    Run recovery in order: category → status → userfield → product_property → product_property_enum.
    Within each type, rows are processed in deterministic order (by id from list).
    Userfield enumeration IDs are persisted during _sync_userfields when matching or creating list-type userfields.
    """
    logger.info("Starting constant-entity startup sync")
    await _sync_categories(db, client)
    await _sync_statuses(db, client)
    await _sync_userfields(db, client)
    await _sync_product_properties(db, client)
    await _sync_product_property_enums(db, client)
    logger.info("Constant-entity startup sync completed")
