"""Build ProductCreate/ProductUpdate from Order per docs/attribute_data_mapping.md (Product table)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.dto.product import Product, ProductCreate, ProductUpdate
from backend.bitrix24.repositories import constant_entity_repository as const_repo
from backend.models import Order
from backend.bitrix24.repositories.mapping_repository import (
    get_bitrix_id,
    get_maas_id,
    get_mapping_by_maas_id,
)
from backend.bitrix24.sync_payload.external_lists import (
    fetch_list_values,
    resolve_order_list_value,
    resolve_product_list_value_to_external_id,
)
from backend.core.config import BITRIX_PRODUCT_IBLOCK_ID
from backend.documents.service import get_document_data_as_base64, get_documents_by_ids
from backend.files.service import get_file_data_as_base64, get_file_by_id

# Field codes that require file payload (fileData: [filename, base64])
FILE_FIELD_3D_MODEL = "UP_CAT_3D_MODEL"
FILE_FIELD_DOC = "UP_CAT_DOC"


class _FieldSpec(NamedTuple):
    """Single product property mapping: Bitrix code, order attribute, use enum resolution."""

    code: str
    order_attr: str | None
    is_list_type: bool


_PRODUCT_FIELD_SPECS: list[_FieldSpec] = [
    _FieldSpec("UP_CAT_MAAS_ID", "order_id", False),
    _FieldSpec("name", "order_name", False),
    _FieldSpec("code", "order_code", False),
    _FieldSpec("UP_CAT_SERVICE", "service_id", True),
    _FieldSpec("UP_CAT_MATERIAL", "material_id", True),
    _FieldSpec("UP_CAT_ROUGHNESS", "finish_id", True),
    _FieldSpec("UP_CAT_ACCURACY", "tolerance_id", True),
    # _FieldSpec("UP_CAT_EQUIPMENT", "suitable_machines", False),
    _FieldSpec("UP_CAT_FINISHING", "cover_id", True),
    _FieldSpec("UP_CAT_CONTROL", "k_otk", True),
    _FieldSpec("UP_CAT_PROD_TIME", "manufacturing_cycle", False),
    _FieldSpec(FILE_FIELD_3D_MODEL, "file_id", False),
    _FieldSpec(FILE_FIELD_DOC, "document_ids", False),
    _FieldSpec("length", "length", False),
    _FieldSpec("width", "width", False),
    _FieldSpec("height", "height", False),
    _FieldSpec("UP_CAT_VOLUME", "mat_volume", False),
    _FieldSpec("UP_CAT_CONS_RATE", "mat_weight", False),
    _FieldSpec("UP_CAT_MAIN_MAT", None, False),
    _FieldSpec("UP_CAT_SUP_MAT", None, False),
    _FieldSpec("UP_CAT_INTENSITY", "total_time", False),
    _FieldSpec("UP_CAT_STND_HR_COST", None, False),
    _FieldSpec("UP_CAT_SPEC_EQ_COST", None, False),
]

# total_price_breakdown JSON keys for fields without a direct order attr
_BREAKDOWN_KEYS: dict[str, str] = {
    "UP_CAT_MAIN_MAT": "mat_price",
    "UP_CAT_SUP_MAT": "dop_mat_price",
    "UP_CAT_STND_HR_COST": "price_of_hour_with_others",
    "UP_CAT_SPEC_EQ_COST": "price_special_equipment_to_quantity",
}


def _parse_breakdown(order: Order) -> dict[str, Any] | None:
    """Parse order.total_price_breakdown (JSON string or dict) to a dict."""
    raw = getattr(order, "total_price_breakdown", None)
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def parse_breakdown_from_order(order: Order) -> dict[str, Any] | None:
    """Parse order.total_price_breakdown to a dict. Public for reverse sync merge."""
    return _parse_breakdown(order)


def _get_order_value_for_property(
    order: Order, order_attr: str | None, property_code: str
) -> Any:
    """Value from order for a product property; uses total_price_breakdown for breakdown-only codes."""
    if order_attr is not None:
        return getattr(order, order_attr, None)
    breakdown_key = _BREAKDOWN_KEYS.get(property_code)
    if breakdown_key is None:
        return None
    breakdown = _parse_breakdown(order)
    return breakdown.get(breakdown_key) if breakdown else None


def _bitrix_property_key(bitrix_property_id: int) -> str:
    """Bitrix property key: 'property' + ID."""
    return f"property{bitrix_property_id}"


def _parse_document_ids(value: Any) -> list[int]:
    """Parse order.document_ids (JSON string or list) to list of ints."""
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value if x is not None]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return [int(x) for x in (parsed if isinstance(parsed, list) else []) if x is not None]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    return []


async def _build_3d_model_property_value(
    db: AsyncSession, file_id: int
) -> dict[str, Any] | None:
    """Build UP_CAT_3D_MODEL value: {\"value\": {\"fileData\": [filename, base64]}}."""
    file_record = await get_file_by_id(db, file_id)
    if not file_record:
        return None
    base64_data = await get_file_data_as_base64(file_record)
    if not base64_data:
        return None
    filename = getattr(file_record, "original_filename", None) or getattr(
        file_record, "filename", "file"
    )
    return {"value": {"fileData": [filename, base64_data]}}


async def _build_documents_property_values(
    db: AsyncSession, document_ids: list[int]
) -> list[dict[str, Any]]:
    """Build UP_CAT_DOC values: list of {\"value\": {\"fileData\": [filename, base64]}}."""
    if not document_ids:
        return []
    documents = await get_documents_by_ids(db, document_ids)
    pairs = await asyncio.gather(
        *[get_document_data_as_base64(doc) for doc in documents]
    )
    return [
        {"value": {"fileData": [pair[0], pair[1]]}}
        for pair in pairs
        if pair is not None
    ]


async def _build_property_code_maps_from_rows(
    db: AsyncSession, rows: list[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    """Build property_code → Bitrix ID and property_code → maas_id from property rows."""
    code_to_bitrix_id: dict[str, int] = {}
    code_to_maas_id: dict[str, int] = {}
    for row in rows:
        code = getattr(row, "code", None)
        if not code:
            continue
        code_to_maas_id[code] = row.id
        bitrix_id = await get_bitrix_id(db, row.id, const_repo.ENTITY_TYPE_PRODUCT_PROPERTY)
        if bitrix_id is not None:
            code_to_bitrix_id[code] = bitrix_id
    return code_to_bitrix_id, code_to_maas_id


async def _enum_label_to_bitrix_id(
    db: AsyncSession, property_maas_id: int, label: Any
) -> int | None:
    """Resolve a single enum label to Bitrix enumeration ID."""
    if label is None:
        return None
    search_label = str(label).strip()
    enum_rows = await const_repo.product_property_enum_list_by_property(
        db, property_maas_id, limit=500
    )
    for enum_row in enum_rows:
        value_match = getattr(enum_row, "value", None) and str(enum_row.value).strip() == search_label
        xml_id_match = getattr(enum_row, "xml_id", None) and str(enum_row.xml_id).strip() == search_label
        if value_match or xml_id_match:
            return await get_bitrix_id(
                db, enum_row.id, const_repo.ENTITY_TYPE_PRODUCT_PROPERTY_ENUM
            )
    return None


async def _enum_labels_to_bitrix_ids(
    db: AsyncSession, property_maas_id: int, labels: list[Any]
) -> list[int]:
    """Resolve list of enum labels to Bitrix enum IDs; skip unresolved."""
    bitrix_ids: list[int] = []
    for lbl in labels:
        bitrix_id = await _enum_label_to_bitrix_id(db, property_maas_id, lbl)
        if bitrix_id is not None:
            bitrix_ids.append(bitrix_id)
    return bitrix_ids


def _assign_scalar_property(
    properties: dict[str, Any], property_key: str, value: Any
) -> None:
    """Set a scalar property value (int, float, or string)."""
    if value is None:
        return
    properties[property_key] = {
        "value": value if isinstance(value, (int, float)) else str(value)
    }


async def _assign_enum_property(
    db: AsyncSession,
    properties: dict[str, Any],
    property_key: str,
    property_code: str,
    raw_value: Any,
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> None:
    """Resolve enum/list value to Bitrix ID(s) and set property."""
    label = resolve_order_list_value(list_values, property_code, raw_value) or raw_value
    prop_maas_id = code_to_maas_id.get(property_code)
    if prop_maas_id is None:
        properties[property_key] = label
        return
    if isinstance(label, list):
        bitrix_ids = await _enum_labels_to_bitrix_ids(db, prop_maas_id, label)
        if bitrix_ids:
            properties[property_key] = bitrix_ids
    else:
        bitrix_id = await _enum_label_to_bitrix_id(db, prop_maas_id, label)
        if bitrix_id is not None:
            properties[property_key] = {"value": bitrix_id}


def _build_remove_entries_for_value_ids(
    value_ids: list[str],
) -> list[dict[str, Any]]:
    """Build Bitrix remove entries: [{\"value\": {\"remove\": \"Y\"}, \"valueId\": \"...\"}, ...]."""
    return [
        {"value": {"remove": "Y"}, "valueId": str(vid)}
        for vid in value_ids
        if vid is not None
    ]


async def _build_product_properties(
    db: AsyncSession,
    order: Order,
    code_to_bitrix_id: dict[str, int],
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> dict[str, Any]:
    """Build product properties dict: key = Bitrix property key, value = scalar, enum ID(s), or fileData."""
    properties: dict[str, Any] = {}
    order_id = getattr(order, "order_id", None)
    product_mapping = (
        await get_mapping_by_maas_id(db, order_id, "product") if order_id else None
    )
    product_buffer: dict[str, Any] = (
        (product_mapping.buffer if isinstance(product_mapping.buffer, dict) else {})
        if product_mapping and product_mapping.buffer
        else {}
    )
    for spec in _PRODUCT_FIELD_SPECS:
        bitrix_prop_id = code_to_bitrix_id.get(spec.code)
        if bitrix_prop_id is None:
            continue
        property_key = _bitrix_property_key(bitrix_prop_id)
        value = _get_order_value_for_property(order, spec.order_attr, spec.code)

        if spec.code == FILE_FIELD_3D_MODEL:
            if value is not None and isinstance(value, int):
                file_value = await _build_3d_model_property_value(db, value)
                if file_value:
                    properties[property_key] = file_value
            continue
        if spec.code == FILE_FIELD_DOC:
            doc_ids = _parse_document_ids(value)
            doc_values = (
                await _build_documents_property_values(db, doc_ids) if doc_ids else []
            )
            existing_value_ids = product_buffer.get(property_key)
            if isinstance(existing_value_ids, list) and existing_value_ids:
                remove_entries = _build_remove_entries_for_value_ids(existing_value_ids)
                properties[property_key] = remove_entries + doc_values
            elif doc_values:
                properties[property_key] = doc_values
            continue
        if value is None:
            continue
        if spec.is_list_type:
            await _assign_enum_property(
                db, properties, property_key, spec.code, value,
                code_to_maas_id, list_values,
            )
        else:
            _assign_scalar_property(properties, property_key, value)
    return properties


async def _load_property_code_maps(
    db: AsyncSession, iblock_id: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Load property_code → Bitrix ID and property_code → maas_id in a single pass."""
    rows = await const_repo.product_property_list(db, iblock_id=iblock_id, limit=500)
    return await _build_property_code_maps_from_rows(db, rows)


def _build_product_base_fields(order: Order) -> dict[str, Any]:
    """Build common scalar fields for ProductCreate/Update from order."""
    order_id = getattr(order, "order_id", "")
    return {
        "name": getattr(order, "order_name", None) or f"Order {order_id}",
        "code": getattr(order, "order_code", None),
        "length": float(x) if (x := getattr(order, "length", None)) is not None else None,
        "width": float(x) if (x := getattr(order, "width", None)) is not None else None,
        "height": float(x) if (x := getattr(order, "height", None)) is not None else None,
    }


async def order_to_product_create(db: AsyncSession, order: Order) -> ProductCreate:
    """Build ProductCreate from Order; resolves external IDs to labels, then to Bitrix enum IDs."""
    if BITRIX_PRODUCT_IBLOCK_ID <= 0:
        raise ValueError("BITRIX_PRODUCT_IBLOCK_ID must be set for product sync (config or env)")
    code_to_bitrix_id, code_to_maas_id = await _load_property_code_maps(db, BITRIX_PRODUCT_IBLOCK_ID)
    list_values = await fetch_list_values()
    properties = await _build_product_properties(
        db, order, code_to_bitrix_id, code_to_maas_id, list_values
    )
    return ProductCreate(
        iblockId=BITRIX_PRODUCT_IBLOCK_ID,
        **_build_product_base_fields(order),
        properties=properties or None,
    )


async def order_to_product_update(db: AsyncSession, order: Order) -> ProductUpdate:
    """Build ProductUpdate from Order (same property resolution as create)."""
    if BITRIX_PRODUCT_IBLOCK_ID <= 0:
        raise ValueError("BITRIX_PRODUCT_IBLOCK_ID must be set for product sync (config or env)")
    code_to_bitrix_id, code_to_maas_id = await _load_property_code_maps(db, BITRIX_PRODUCT_IBLOCK_ID)
    list_values = await fetch_list_values()
    properties = await _build_product_properties(
        db, order, code_to_bitrix_id, code_to_maas_id, list_values
    )
    return ProductUpdate(
        **_build_product_base_fields(order),
        properties=properties or None,
    )


def _bitrix_property_key_to_id(property_key: str) -> int | None:
    """Parse 'property123' → 123."""
    if not property_key or not property_key.startswith("property"):
        return None
    try:
        return int(property_key[8:])
    except ValueError:
        return None


def _extract_scalar_from_property_value(value: Any) -> Any:
    """Extract a single scalar from Bitrix property value (dict with 'value' or list of dicts)."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("value")
    if isinstance(value, list) and value:
        first = value[0]
        return first.get("value") if isinstance(first, dict) else None
    return None


def _extract_bitrix_enum_ids_from_property_value(value: Any) -> list[int]:
    """Extract Bitrix enum ID(s) from property value: single {\"value\": id} or list of ids/dicts."""
    if value is None:
        return []
    if isinstance(value, dict):
        v = value.get("value")
        if v is not None:
            try:
                return [int(v)]
            except (TypeError, ValueError):
                pass
        return []
    if isinstance(value, list):
        bitrix_ids: list[int] = []
        for item in value:
            v = item.get("value") if isinstance(item, dict) else item
            if v is not None:
                try:
                    bitrix_ids.append(int(v))
                except (TypeError, ValueError):
                    pass
        return bitrix_ids
    return []


async def _build_bitrix_property_id_to_code(
    db: AsyncSession, iblock_id: int
) -> dict[int, str]:
    """Build mapping Bitrix property ID → property code from constant entity repo."""
    rows = await const_repo.product_property_list(db, iblock_id=iblock_id, limit=500)
    bitrix_id_to_code: dict[int, str] = {}
    for row in rows:
        code = getattr(row, "code", None)
        if not code:
            continue
        bitrix_id = await get_bitrix_id(db, row.id, const_repo.ENTITY_TYPE_PRODUCT_PROPERTY)
        if bitrix_id is not None:
            bitrix_id_to_code[int(bitrix_id)] = code
    return bitrix_id_to_code


# --- Reverse: Bitrix Product → Order ---


async def _bitrix_enum_id_to_label(
    db: AsyncSession, property_maas_id: int, bitrix_enum_id: Any
) -> str | None:
    """Resolve Bitrix enum ID to enum value (label). Reverse of _enum_label_to_bitrix_id."""
    if bitrix_enum_id is None:
        return None
    try:
        enum_id = int(bitrix_enum_id)
    except (TypeError, ValueError):
        return None
    maas_enum_id = await get_maas_id(
        db, enum_id, const_repo.ENTITY_TYPE_PRODUCT_PROPERTY_ENUM
    )
    if maas_enum_id is None:
        return None
    enum_row = await const_repo.product_property_enum_get_by_id(db, maas_enum_id)
    if enum_row is None:
        return None
    value = getattr(enum_row, "value", None) or getattr(enum_row, "xml_id", None)
    return str(value).strip() if value is not None else None


async def _bitrix_enum_ids_to_labels(
    db: AsyncSession, property_maas_id: int, bitrix_enum_ids: list[int]
) -> list[str]:
    """Resolve list of Bitrix enum IDs to labels. Reverse of _enum_labels_to_bitrix_ids."""
    labels: list[str] = []
    for bitrix_id in bitrix_enum_ids:
        label = await _bitrix_enum_id_to_label(db, property_maas_id, bitrix_id)
        if label is not None:
            labels.append(label)
    return labels


def _build_order_base_fields_from_product(
    product_data: dict[str, Any],
) -> dict[str, Any]:
    """Build common order fields from product (order_name, order_code, length, width, height)."""
    base: dict[str, Any] = {
        "order_name": product_data.get("name"),
        "order_code": product_data.get("code"),
    }
    for key in ("length", "width", "height"):
        v = product_data.get(key)
        if v is not None:
            try:
                base[key] = float(v)
            except (TypeError, ValueError):
                base[key] = v
    return base


# property_code → total_price_breakdown key (reverse of _BREAKDOWN_KEYS)
_BREAKDOWN_KEYS_REVERSE: dict[str, str] = {
    "UP_CAT_MAIN_MAT": "mat_price",
    "UP_CAT_SUP_MAT": "dop_mat_price",
    "UP_CAT_STND_HR_COST": "price_of_hour_with_others",
    "UP_CAT_SPEC_EQ_COST": "price_special_equipment_to_quantity",
}


async def _assign_order_enum_from_property(
    db: AsyncSession,
    payload: dict[str, Any],
    order_attr: str | None,
    property_code: str,
    property_value: Any,
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> None:
    """Resolve Bitrix enum ID(s) to label(s), then to external id(s); set order payload. Reverse of _assign_enum_property."""
    bitrix_enum_ids = _extract_bitrix_enum_ids_from_property_value(property_value)
    if not bitrix_enum_ids:
        return
    prop_maas_id = code_to_maas_id.get(property_code)
    if prop_maas_id is None:
        if isinstance(property_value, dict) and "value" in property_value:
            payload[order_attr] = property_value.get("value")
        return
    labels = await _bitrix_enum_ids_to_labels(db, prop_maas_id, bitrix_enum_ids)
    if not labels:
        return
    external_id = resolve_product_list_value_to_external_id(
        list_values, property_code,
        labels[0] if len(labels) == 1 else labels,
    )
    if external_id is not None and order_attr is not None:
        payload[order_attr] = external_id


def _assign_order_scalar_from_property(
    payload: dict[str, Any],
    order_attr: str | None,
    property_code: str,
    property_value: Any,
    breakdown: dict[str, Any],
) -> None:
    """Set scalar or breakdown entry from Bitrix property value. Reverse of _assign_scalar_property / _get_order_value_for_property."""
    scalar = _extract_scalar_from_property_value(property_value)
    if scalar is None:
        return
    if order_attr is not None:
        payload[order_attr] = (
            scalar if isinstance(scalar, (int, float)) else str(scalar)
        )
    else:
        breakdown_key = _BREAKDOWN_KEYS_REVERSE.get(property_code)
        if breakdown_key is not None:
            try:
                breakdown[breakdown_key] = (
                    float(scalar) if isinstance(scalar, (int, float)) else scalar
                )
            except (TypeError, ValueError):
                breakdown[breakdown_key] = scalar


async def _build_order_payload_from_product_properties(
    db: AsyncSession,
    product_data: dict[str, Any],
    bitrix_id_to_code: dict[int, str],
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> dict[str, Any]:
    """Build order update payload from product properties. Reverse of _build_product_properties."""
    payload: dict[str, Any] = {}
    breakdown: dict[str, Any] = {}
    code_to_spec = {s.code: s for s in _PRODUCT_FIELD_SPECS}
    for property_key, property_value in (product_data or {}).items():
        prop_id = _bitrix_property_key_to_id(property_key)
        if prop_id is None:
            continue
        property_code = bitrix_id_to_code.get(prop_id)
        if not property_code:
            continue
        spec = code_to_spec.get(property_code)
        if spec is None:
            continue
        if spec.code == FILE_FIELD_3D_MODEL or spec.code == FILE_FIELD_DOC:
            continue
        if spec.is_list_type:
            await _assign_order_enum_from_property(
                db, payload, spec.order_attr, property_code, property_value,
                code_to_maas_id, list_values,
            )
        else:
            _assign_order_scalar_from_property(
                payload, spec.order_attr, property_code, property_value, breakdown,
            )
    if breakdown:
        payload["total_price_breakdown"] = breakdown
    return payload


async def product_to_order_update(
    db: AsyncSession,
    product: Product,
    *,
    current_breakdown: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Order update payload from Bitrix Product. Reverse of order_to_product_*.
    If current_breakdown is provided, total_price_breakdown is merged (current keys preserved, Bitrix overlay).
    """
    if BITRIX_PRODUCT_IBLOCK_ID <= 0:
        raise ValueError("BITRIX_PRODUCT_IBLOCK_ID must be set for product sync (config or env)")
    product_data = product.to_dict()
    code_to_bitrix_id, code_to_maas_id = await _load_property_code_maps(
        db, BITRIX_PRODUCT_IBLOCK_ID
    )
    bitrix_id_to_code = {bid: code for code, bid in code_to_bitrix_id.items()}
    list_values = await fetch_list_values()
    base_fields = _build_order_base_fields_from_product(product_data)
    property_fields = await _build_order_payload_from_product_properties(
        db, product_data, bitrix_id_to_code, code_to_maas_id, list_values
    )
    payload: dict[str, Any] = {**base_fields, **property_fields}
    if current_breakdown is not None and "total_price_breakdown" in payload:
        payload["total_price_breakdown"] = {
            **current_breakdown,
            **payload["total_price_breakdown"],
        }
    return {k: v for k, v in payload.items() if v is not None}
