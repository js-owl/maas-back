"""
Initial data for Bitrix24 constant-entity tables (userfields, product properties).

Source: docs/attribute_data_mapping.md. Seeding runs when tables are empty so that
startup sync can create or match these entities in Bitrix24 and store external IDs.

Entity store holds attribute definitions; only fields that are present are sent on
initialization, so definitions can omit optional fields.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import BitrixUserfield, BitrixProductProperty
from backend.bitrix24.repositories import constant_entity_repository as repo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENUMS_KEY = "enums"
_KIND_KEY = "kind"
_SORT_STEP = 100
_DEF_ENUM = "N"
_ENTITY_DEAL = "CRM_DEAL"

_KIND_DEAL = "deal_userfield"
_KIND_PRODUCT = "product_property"


def _enum_sort(index: int) -> int:
    """Sort value for enumeration item (must be a multiple of 100)."""
    return index * _SORT_STEP


def _enum_xml_id(prefix: str, index: int) -> str:
    """Unique xml_id for enumeration item."""
    return f"{prefix}_{index}"


# ---------------------------------------------------------------------------
# Entity store (single list; init uses only present fields)
# ---------------------------------------------------------------------------


class EntityStore:
    """
    Mutable store of entity attribute definitions for seeding.
    Payloads are built by including only present (non-None) fields,
    so initialization works even when not all fields are provided.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def add_deal(
        self,
        *,
        # Required (with defaults where entity is fixed)
        entity_id: str = _ENTITY_DEAL,
        field_name: str,
        user_type_id: str,
        label: str,
        # Optional: all supported Bitrix userfield fields
        xml_id: str | None = None,
        sort: int | None = None,
        multiple: str | None = None,
        mandatory: str | None = None,
        show_filter: str | None = None,
        show_in_list: str | None = None,
        edit_in_list: str | None = None,
        is_searchable: str | None = None,
        edit_form_label: dict[str, str] | None = None,
        list_column_label: dict[str, str] | None = None,
        list_filter_label: dict[str, str] | None = None,
        error_message: dict[str, str] | None = None,
        help_message: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None,
        # List/enum values (stored separately; not sent as LIST to repo)
        enums: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a deal userfield. Accepts all Bitrix userfield fields; only non-None are used on init."""
        entry: dict[str, Any] = {
            _KIND_KEY: _KIND_DEAL,
            "ENTITY_ID": entity_id,
            "FIELD_NAME": field_name,
            "USER_TYPE_ID": user_type_id,
            "LABEL": label,
        }
        if xml_id is not None:
            entry["XML_ID"] = xml_id
        if sort is not None:
            entry["SORT"] = sort
        if multiple is not None:
            entry["MULTIPLE"] = multiple
        if mandatory is not None:
            entry["MANDATORY"] = mandatory
        if show_filter is not None:
            entry["SHOW_FILTER"] = show_filter
        if show_in_list is not None:
            entry["SHOW_IN_LIST"] = show_in_list
        if edit_in_list is not None:
            entry["EDIT_IN_LIST"] = edit_in_list
        if is_searchable is not None:
            entry["IS_SEARCHABLE"] = is_searchable
        if edit_form_label is not None:
            entry["EDIT_FORM_LABEL"] = edit_form_label
        if list_column_label is not None:
            entry["LIST_COLUMN_LABEL"] = list_column_label
        if list_filter_label is not None:
            entry["LIST_FILTER_LABEL"] = list_filter_label
        if error_message is not None:
            entry["ERROR_MESSAGE"] = error_message
        if help_message is not None:
            entry["HELP_MESSAGE"] = help_message
        if settings is not None:
            entry["SETTINGS"] = settings
        if enums is not None:
            entry[_ENUMS_KEY] = enums
        self._entries.append(entry)
        return entry

    def add_product(
        self,
        *,
        # Required
        code: str,
        name: str,
        property_type: str,
        # Optional: all supported Bitrix product property fields (camelCase for repo)
        xml_id: str | None = None,
        active: str | None = None,
        sort: int | None = None,
        is_required: str | None = None,
        multiple: str | None = None,
        multiple_cnt: int | None = None,
        with_description: str | None = None,
        hint: str | None = None,
        row_count: int | None = None,
        col_count: int | None = None,
        searchable: str | None = None,
        filtrable: str | None = None,
        default_value: str | None = None,
        list_type: str | None = None,
        link_iblock_id: int | None = None,
        file_type: str | None = None,
        user_type: str | None = None,
        user_type_settings: dict[str, Any] | None = None,
        # List/enum values
        enums: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a product property. Accepts all Bitrix product property fields; only non-None are used on init."""
        entry: dict[str, Any] = {
            _KIND_KEY: _KIND_PRODUCT,
            "code": code,
            "name": name,
            "propertyType": property_type,
        }
        if xml_id is not None:
            entry["xmlId"] = xml_id
        if active is not None:
            entry["active"] = active
        if sort is not None:
            entry["sort"] = sort
        if is_required is not None:
            entry["isRequired"] = is_required
        if multiple is not None:
            entry["multiple"] = multiple
        if multiple_cnt is not None:
            entry["multipleCnt"] = multiple_cnt
        if with_description is not None:
            entry["withDescription"] = with_description
        if hint is not None:
            entry["hint"] = hint
        if row_count is not None:
            entry["rowCount"] = row_count
        if col_count is not None:
            entry["colCount"] = col_count
        if searchable is not None:
            entry["searchable"] = searchable
        if filtrable is not None:
            entry["filtrable"] = filtrable
        if default_value is not None:
            entry["defaultValue"] = default_value
        if list_type is not None:
            entry["listType"] = list_type
        if link_iblock_id is not None:
            entry["linkIblockId"] = link_iblock_id
        if file_type is not None:
            entry["fileType"] = file_type
        if user_type is not None:
            entry["userType"] = user_type
        if user_type_settings is not None:
            entry["userTypeSettings"] = user_type_settings
        if enums is not None:
            entry[_ENUMS_KEY] = enums
        self._entries.append(entry)
        return entry

    def deal_entries(self) -> list[dict[str, Any]]:
        return [e for e in self._entries if e.get(_KIND_KEY) == _KIND_DEAL]

    def product_entries(self) -> list[dict[str, Any]]:
        return [e for e in self._entries if e.get(_KIND_KEY) == _KIND_PRODUCT]

    def all_entries(self) -> list[dict[str, Any]]:
        return list(self._entries)


# ---------------------------------------------------------------------------
# Payload builders (only include present fields; safe for partial definitions)
# ---------------------------------------------------------------------------


def _userfield_payload(entry: dict[str, Any]) -> dict[str, Any]:
    """Build userfield create payload from store entry; omit enums and None."""
    return {
        k: v for k, v in entry.items()
        if k not in (_KIND_KEY, _ENUMS_KEY) and v is not None
    }


def _product_property_payload(entry: dict[str, Any], iblock_id: int) -> dict[str, Any]:
    """Build product property create payload from store entry; omit enums and None; inject iblockId."""
    payload: dict[str, Any] = {
        k: v for k, v in entry.items()
        if k not in (_KIND_KEY, _ENUMS_KEY) and v is not None
    }
    payload["iblockId"] = iblock_id
    return payload


# ---------------------------------------------------------------------------
# Seed: one entity (uses payload with only present fields)
# ---------------------------------------------------------------------------


async def _seed_one_userfield(db: AsyncSession, entry: dict[str, Any]) -> None:
    """Create one userfield from store entry; then create enum rows if enums present."""
    payload = _userfield_payload(entry)
    uf = await repo.userfield_create(db, payload)
    enums = entry.get(_ENUMS_KEY)
    if not enums:
        return
    prefix = payload.get("XML_ID") or payload.get("FIELD_NAME", "UF")
    for idx, value in enumerate(enums, start=1):
        await repo.userfield_enum_create(
            db,
            userfield_id=uf.id,
            sort=_enum_sort(idx),
            value=value,
            def_=_DEF_ENUM,
            xml_id=_enum_xml_id(prefix, idx),
        )


async def _seed_one_product_property(
    db: AsyncSession, entry: dict[str, Any], iblock_id: int
) -> None:
    """Create one product property from store entry; then create enum rows if enums present."""
    payload = _product_property_payload(entry, iblock_id)
    prop = await repo.product_property_create(db, payload)
    enums = entry.get(_ENUMS_KEY)
    if not enums:
        return
    prefix = entry.get("xmlId") or entry.get("code", "P")
    for idx, value in enumerate(enums, start=1):
        await repo.product_property_enum_create(
            db,
            property_id=prop.id,
            value=value,
            xml_id=_enum_xml_id(prefix, idx),
            def_=_DEF_ENUM,
            sort=_enum_sort(idx),
        )


# ---------------------------------------------------------------------------
# Seed: full tables (idempotent, driven by entity store)
# ---------------------------------------------------------------------------


async def _seed_constant_entities(db: AsyncSession, iblock_id: int, store: EntityStore) -> None:
    """Seed all entities from store; only present fields are sent."""
    deal_entries = store.deal_entries()
    product_entries = store.product_entries()

    if deal_entries:
        result = await db.execute(select(BitrixUserfield).limit(1))
        if result.first() is None:
            for entry in deal_entries:
                await _seed_one_userfield(db, entry)
            logger.info("Seeded %d deal userfields", len(deal_entries))
        else:
            logger.debug("Userfields already present, skipping deal userfield seed")

    if product_entries and iblock_id > 0:
        result = await db.execute(select(BitrixProductProperty).limit(1))
        if result.first() is None:
            for entry in product_entries:
                await _seed_one_product_property(db, entry, iblock_id)
            logger.info("Seeded %d product properties (iblock_id=%s)", len(product_entries), iblock_id)
        else:
            logger.debug("Product properties already present, skipping seed")
    elif product_entries and iblock_id <= 0:
        logger.debug("iblock_id=%s <= 0, skipping product property seed", iblock_id)


# ---------------------------------------------------------------------------
# Entity store initialization (single place to define all attributes)
# Source: docs/attribute_data_mapping.md
# ---------------------------------------------------------------------------

def _create_entity_store() -> EntityStore:
    """Build the default entity store with all seed attributes. Add or change attributes here."""
    store = EntityStore()

    # --- Deal userfields (CRM_DEAL) ---
    store.add_deal(
        field_name="UF_CRM_MANUFACTURER",
        user_type_id="enumeration",
        label="Предприятие-изготовитель",
        xml_id="MANUFACTURER",
        enums=["ЦКП", 'АО "КТ-Спектр"', 'АО "ДМЗ"'],
    )
    store.add_deal(
        field_name="UF_CRM_MAAS_ID",
        user_type_id="integer",
        label="Идентификатор сделки в Maas",
        xml_id="MAAS_ID",
    )
    store.add_deal(
        field_name="UF_CRM_SHIPPING_COST",
        user_type_id="double",
        label="Стоимость доставки",
        xml_id="SHIPPING_COST",
    )

    # --- Catalog product properties (UP_CAT_*) ---
    store.add_product(
        code="UP_CAT_SERVICE",
        name="Услуга",
        property_type="L",
        xml_id="SERVICE",
        list_type="L",
        enums=[
            "3D-печать",
            "Механическая обработка",
            "Листогибочные работы",
            "Слесарные работы",
            "Термическая обработка",
            "Лазерная резка",
            "Шлифование",
            "Сварочные работы",
            "Покрасочные работы",
        ],
    )
    store.add_product(
        code="UP_CAT_MATERIAL",
        name="Материал",
        property_type="L",
        xml_id="MATERIAL",
        list_type="L",
        enums=[
            "Алюминий 1163",
            "Алюминий АД1",
            "Алюминий АД31",
            "Алюминий АК4",
            "Алюминий АМг3",
            "Алюминий АМг6",
            "Алюминий АМц",
            "Алюминий В95оч",
            "Алюминий Д16",
            "Алюминий Д16Т",
            "Бронза БрАЖМц10-3-1.5",
            "Латунь Л63",
            "Порошок PA11",
            "Порошок PA12",
            "Сталь 12Х18Н10Т",
            "Сталь 14Х17Н2",
            "Сталь 20",
            "Сталь 30ХГСА",
            "Сталь 40Х",
            "Сталь 40Х13",
            "Сталь 45",
        ],
    )
    store.add_product(
        code="UP_CAT_ROUGHNESS",
        name="Шероховатость",
        property_type="L",
        xml_id="ROUGHNESS",
        list_type="L",
        enums=["12.5", "6.3", "3.2", "1.6", "0.8"],
    )
    store.add_product(
        code="UP_CAT_ACCURACY",
        name="Квалитет точности",
        property_type="L",
        xml_id="ACCURACY",
        list_type="L",
        enums=["IT7", "IT8", "IT9", "IT10", "IT11", "IT12"],
    )
    store.add_product(
        code="UP_CAT_FINISHING",
        name="Финишная обработка изделия",
        property_type="L",
        xml_id="FINISHING",
        list_type="L",
        multiple="Y",
        enums=["Покраска", "Гальваника"],
    )
    store.add_product(
        code="UP_CAT_CONTROL",
        name="Вид контроля",
        property_type="L",
        xml_id="CONTROL",
        list_type="L",
        enums=["Изготовителя", "Заказчика на площадке изготовителя", "Независимой приёмкой"],
    )
    store.add_product(
        code="UP_CAT_MAAS_ID",
        name="Идентификатор товара в Maas",
        property_type="N",
        xml_id="MAAS_ID",
    )
    # store.add_product(
    #     code="UP_CAT_EQUIPMENT",
    #     name="Подходящее оборудование",
    #     property_type="S",
    #     xml_id="EQUIPMENT",
    # )
    store.add_product(
        code="UP_CAT_PROD_TIME",
        name="Время изготовления, дней",
        property_type="N",
        xml_id="PROD_TIME",
    )
    store.add_product(
        code="UP_CAT_3D_MODEL",
        name="3D-модель",
        property_type="F",
        xml_id="3D_MODEL",
    )
    store.add_product(
        code="UP_CAT_DOC",
        name="Чертежи, документация",
        property_type="F",
        xml_id="DOC",
        multiple="Y",
    )
    store.add_product(
        code="UP_CAT_VOLUME",
        name="Объём заготовки",
        property_type="N",
        xml_id="VOLUME",
    )
    store.add_product(
        code="UP_CAT_CONS_RATE",
        name="Норма расхода",
        property_type="N",
        xml_id="CONS_RATE",
    )
    store.add_product(
        code="UP_CAT_MAIN_MAT",
        name="Основной материал",
        property_type="N",
        xml_id="MAIN_MAT",
    )
    store.add_product(
        code="UP_CAT_SUP_MAT",
        name="Вспомогательные материалы",
        property_type="N",
        xml_id="SUP_MAT",
    )
    store.add_product(
        code="UP_CAT_INTENSITY",
        name="Трудоёмкость",
        property_type="N",
        xml_id="INTENSITY",
    )
    store.add_product(
        code="UP_CAT_STND_HR_COST",
        name="Стоимость нормочаса",
        property_type="N",
        xml_id="STND_HR_COST",
    )
    store.add_product(
        code="UP_CAT_SPEC_EQ_COST",
        name="Затраты на специальную технологическую оснастку",
        property_type="N",
        xml_id="SPEC_EQ_COST",
    )

    return store


# Lazy singleton for default store (so callers can use ENTITY_STORE or pass custom store)
_entity_store: EntityStore | None = None


def get_entity_store() -> EntityStore:
    """Return the default entity store; create on first use."""
    global _entity_store
    if _entity_store is None:
        _entity_store = _create_entity_store()
    return _entity_store


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def seed_constant_entity_initial_data(
    db: AsyncSession,
    iblock_id: int,
    *,
    store: EntityStore | None = None,
) -> None:
    """
    Insert initial deal userfields and catalog product properties from the entity store.

    Idempotent: no-op when tables already have rows. Product properties only when iblock_id > 0.
    Only fields that are set on each store entry are sent (partial definitions are supported).
    Pass a custom store to override the default; otherwise get_entity_store() is used.
    """
    target = store if store is not None else get_entity_store()
    await _seed_constant_entities(db, iblock_id, target)
