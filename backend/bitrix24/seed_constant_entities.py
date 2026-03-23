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

# Maps product property code → key in the list_values dict from fetch_list_values().
# Used to override static enums with live labels from the calculator service.
_PRODUCT_CODE_TO_LIST_KEY: dict[str, str] = {
    "UP_CAT_MATERIAL": "materials",
    "UP_CAT_SERVICE": "services",
    "UP_CAT_ACCURACY": "tolerance",
    "UP_CAT_ROUGHNESS": "finish",
    "UP_CAT_FINISHING": "cover",
    "UP_CAT_CONTROL": "control_types",
    "UP_CAT_CERTIFICATES": "cert_costs",
}

# Maps deal userfield name → key in list_values dict.
# Empty: no deal list fields are currently backed by external lists.
_DEAL_FIELD_TO_LIST_KEY: dict[str, str] = {
    "UF_CRM_MANUFACTURER": "locations",
}


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
# External-list enum resolution helpers
# ---------------------------------------------------------------------------


def _labels_from_list_values(list_values: dict[str, Any], list_key: str) -> list[str]:
    """Extract display labels from a list_values entry (produced by fetch_list_values()).

    Items are expected to be dicts with a ``label`` key (e.g. ``{"id": …, "label": …}``).
    Plain string items are used as-is for forward compatibility.
    """
    items = list_values.get(list_key) or []
    labels: list[str] = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("label")
            if label is not None:
                labels.append(str(label))
        elif item is not None:
            labels.append(str(item))
    return labels


def _resolve_entry_enums(
    entry: dict[str, Any],
    list_values: dict[str, Any] | None,
) -> list[str] | None:
    """Return enum labels for a store entry.

    When ``list_values`` is provided and the entry maps to an external list,
    live labels from that list take precedence over the static ``enums`` defined
    in the store. Falls back to the static enums when the external list is absent
    or returns no items.
    """
    if list_values:
        kind = entry.get(_KIND_KEY)
        if kind == _KIND_PRODUCT:
            list_key = _PRODUCT_CODE_TO_LIST_KEY.get(entry.get("code") or "")
        elif kind == _KIND_DEAL:
            list_key = _DEAL_FIELD_TO_LIST_KEY.get(entry.get("FIELD_NAME") or "")
        else:
            list_key = None
        if list_key:
            labels = _labels_from_list_values(list_values, list_key)
            if labels:
                return labels
    return entry.get(_ENUMS_KEY)


# ---------------------------------------------------------------------------
# Enum helpers: add only missing values to an existing parent
# ---------------------------------------------------------------------------


async def _seed_missing_userfield_enums(
    db: AsyncSession,
    userfield_id: int,
    prefix: str,
    enums: list[str],
) -> int:
    """Insert enum rows whose ``value`` is not yet present for the given userfield.

    Returns the number of rows actually inserted.
    Position-based ``sort`` and ``xml_id`` are derived from the full expected list
    so that ordering stays consistent even when only a subset is added.
    """
    existing = await repo.userfield_enum_list_by_userfield(db, userfield_id)
    existing_values = {e.value for e in existing}
    added = 0
    for idx, value in enumerate(enums, start=1):
        if value not in existing_values:
            await repo.userfield_enum_create(
                db,
                userfield_id=userfield_id,
                sort=_enum_sort(idx),
                value=value,
                def_=_DEF_ENUM,
                xml_id=_enum_xml_id(prefix, idx),
            )
            added += 1
    return added


async def _seed_missing_product_property_enums(
    db: AsyncSession,
    property_id: int,
    prefix: str,
    enums: list[str],
) -> int:
    """Insert enum rows whose ``value`` is not yet present for the given property.

    Returns the number of rows actually inserted.
    """
    existing = await repo.product_property_enum_list_by_property(db, property_id)
    existing_values = {e.value for e in existing}
    added = 0
    for idx, value in enumerate(enums, start=1):
        if value not in existing_values:
            await repo.product_property_enum_create(
                db,
                property_id=property_id,
                value=value,
                xml_id=_enum_xml_id(prefix, idx),
                def_=_DEF_ENUM,
                sort=_enum_sort(idx),
            )
            added += 1
    return added


# ---------------------------------------------------------------------------
# Seed: one entity (uses payload with only present fields)
# ---------------------------------------------------------------------------


async def _seed_one_userfield(
    db: AsyncSession,
    entry: dict[str, Any],
    list_values: dict[str, Any] | None = None,
) -> BitrixUserfield:
    """Create one userfield from store entry; then create enum rows if enums present.

    When ``list_values`` is provided, enum labels are resolved from the external
    list mapped to this field (via ``_DEAL_FIELD_TO_LIST_KEY``), falling back to
    the static ``enums`` defined in the store entry.
    """
    payload = _userfield_payload(entry)
    uf = await repo.userfield_create(db, payload)
    enums = _resolve_entry_enums(entry, list_values)
    if enums:
        prefix = payload.get("XML_ID") or payload.get("FIELD_NAME", "UF")
        await _seed_missing_userfield_enums(db, uf.id, prefix, enums)
    return uf


async def _seed_one_product_property(
    db: AsyncSession,
    entry: dict[str, Any],
    iblock_id: int,
    list_values: dict[str, Any] | None = None,
) -> BitrixProductProperty:
    """Create one product property from store entry; then create enum rows if enums present.

    When ``list_values`` is provided, enum labels are resolved from the external
    list mapped to this property (via ``_PRODUCT_CODE_TO_LIST_KEY``), falling back
    to the static ``enums`` defined in the store entry.
    """
    payload = _product_property_payload(entry, iblock_id)
    prop = await repo.product_property_create(db, payload)
    enums = _resolve_entry_enums(entry, list_values)
    if enums:
        prefix = entry.get("xmlId") or entry.get("code", "P")
        await _seed_missing_product_property_enums(db, prop.id, prefix, enums)
    return prop


# ---------------------------------------------------------------------------
# Seed: full tables (idempotent, driven by entity store)
# ---------------------------------------------------------------------------


async def _seed_constant_entities(
    db: AsyncSession,
    iblock_id: int,
    store: EntityStore,
    list_values: dict[str, Any] | None = None,
) -> None:
    """Seed all entities from store; only present fields are sent.

    Each store entry is checked individually by its natural key (``FIELD_NAME``
    for userfields, ``code`` for product properties).  Only missing records are
    inserted, so this is safe to run against a partially-populated table.

    When ``list_values`` (from ``fetch_list_values()``) is provided, list-type
    fields whose codes are in ``_PRODUCT_CODE_TO_LIST_KEY`` /
    ``_DEAL_FIELD_TO_LIST_KEY`` will use live labels from the calculator service
    instead of the static fallback enums defined in the store.
    """
    deal_entries = store.deal_entries()
    product_entries = store.product_entries()

    seeded_deals = 0
    added_deal_enums = 0
    for entry in deal_entries:
        field_name = entry.get("FIELD_NAME")
        result = await db.execute(
            select(BitrixUserfield).where(BitrixUserfield.field_name == field_name).limit(1)
        )
        existing_uf = result.scalar_one_or_none()
        if existing_uf is None:
            await _seed_one_userfield(db, entry, list_values)
            seeded_deals += 1
            logger.debug("Seeded deal userfield %s", field_name)
        else:
            enums = _resolve_entry_enums(entry, list_values)
            if enums:
                prefix = existing_uf.xml_id or existing_uf.field_name or "UF"
                added = await _seed_missing_userfield_enums(db, existing_uf.id, prefix, enums)
                if added:
                    added_deal_enums += added
                    logger.debug("Added %d missing enum(s) for userfield %s", added, field_name)
    if seeded_deals:
        logger.info("Seeded %d deal userfield(s)", seeded_deals)
    if added_deal_enums:
        logger.info("Added %d missing deal userfield enum(s)", added_deal_enums)

    if not product_entries:
        return
    if iblock_id <= 0:
        logger.debug("iblock_id=%s <= 0, skipping product property seed", iblock_id)
        return

    seeded_products = 0
    added_product_enums = 0
    for entry in product_entries:
        code = entry.get("code")
        result = await db.execute(
            select(BitrixProductProperty).where(BitrixProductProperty.code == code).limit(1)
        )
        existing_prop = result.scalar_one_or_none()
        if existing_prop is None:
            await _seed_one_product_property(db, entry, iblock_id, list_values)
            seeded_products += 1
            logger.debug("Seeded product property %s", code)
        else:
            enums = _resolve_entry_enums(entry, list_values)
            if enums:
                prefix = existing_prop.xml_id or existing_prop.code or "P"
                added = await _seed_missing_product_property_enums(db, existing_prop.id, prefix, enums)
                if added:
                    added_product_enums += added
                    logger.debug("Added %d missing enum(s) for property %s", added, code)
    if seeded_products:
        logger.info("Seeded %d product propert(ies) (iblock_id=%s)", seeded_products, iblock_id)
    if added_product_enums:
        logger.info("Added %d missing product property enum(s) (iblock_id=%s)", added_product_enums, iblock_id)


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
    list_values: dict[str, Any] | None = None,
) -> None:
    """Insert initial deal userfields and catalog product properties from the entity store.

    Idempotent: no-op when tables already have rows. Product properties only when iblock_id > 0.
    Only fields that are set on each store entry are sent (partial definitions are supported).

    Pass a custom store to override the default; otherwise get_entity_store() is used.

    Pass ``list_values`` (the dict returned by ``fetch_list_values()``) to populate
    list-type field enumerations from the live calculator-service data instead of
    the static fallback labels defined in the store.  Fields not present in
    ``_PRODUCT_CODE_TO_LIST_KEY`` / ``_DEAL_FIELD_TO_LIST_KEY``, or for which the
    external list is empty, fall back to the static enums automatically.
    """
    target = store if store is not None else get_entity_store()
    await _seed_constant_entities(db, iblock_id, target, list_values)
