"""Build ProductCreate/ProductUpdate from Order per docs/attribute_data_mapping.md (Product table)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.dto.product import ProductCreate, ProductUpdate
from backend.bitrix24.repositories import constant_entity_repository as const_repo
from backend.bitrix24.repositories.mapping_repository import (
    get_bitrix_id,
    get_mapping_by_maas_id,
)
from backend.bitrix24.sync_payload.external_lists import (
    fetch_list_values,
    resolve_order_list_value,
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


def _parse_breakdown(order: Any) -> dict | None:
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


def _order_property_value(order: Any, attr: str | None, code: str) -> Any:
    """Value from order for a product field; handles total_price_breakdown for breakdown-only codes."""
    if attr is not None:
        return getattr(order, attr, None)
    breakdown_key = _BREAKDOWN_KEYS.get(code)
    if breakdown_key is None:
        return None
    data = _parse_breakdown(order)
    return data.get(breakdown_key) if data else None


def _property_key(bitrix_prop_id: int) -> str:
    """Bitrix property key: 'property' + ID."""
    return f"property{bitrix_prop_id}"


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


async def _build_file_data_3d_model(db: AsyncSession, file_id: int) -> dict[str, list[str]] | None:
    """Build UP_CAT_3D_MODEL value: {\"fileData\": [\"filename.ext\", \"base64\"]}."""
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


async def _build_file_data_documents(
    db: AsyncSession, document_ids: list[int]
) -> list[dict[str, list[str]]]:
    """Build UP_CAT_DOC value: [{\"fileData\": [\"filename.ext\", \"base64\"]}, ...]."""
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


async def _build_property_maps_from_rows(
    db: AsyncSession, rows: list[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    """Build code -> Bitrix property ID and code -> maas id from same property list rows."""
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


async def _resolve_enum_bitrix_id(
    db: AsyncSession, property_maas_id: int, label: Any
) -> int | None:
    """Resolve a single label to Bitrix enumeration ID."""
    if label is None:
        return None
    str_val = str(label).strip()
    enum_rows = await const_repo.product_property_enum_list_by_property(
        db, property_maas_id, limit=500
    )
    for enum_row in enum_rows:
        if (getattr(enum_row, "value", None) and str(enum_row.value).strip() == str_val) or (
            getattr(enum_row, "xml_id", None) and str(enum_row.xml_id).strip() == str_val
        ):
            return await get_bitrix_id(
                db, enum_row.id, const_repo.ENTITY_TYPE_PRODUCT_PROPERTY_ENUM
            )
    return None


async def _resolve_enum_bitrix_ids(
    db: AsyncSession, property_maas_id: int, labels: list[Any]
) -> list[int]:
    """Resolve list of labels to Bitrix enum IDs (skips unresolved)."""
    out = []
    for val in labels:
        bid = await _resolve_enum_bitrix_id(db, property_maas_id, val)
        if bid is not None:
            out.append(bid)
    return out


def _set_scalar_property(props: dict[str, Any], key: str, value: Any) -> None:
    """Set a scalar property value (int, float, or string)."""
    if value is None:
        return
    props[key] = {"value": value if isinstance(value, (int, float)) else str(value)}


async def _set_enum_property(
    db: AsyncSession,
    props: dict[str, Any],
    key: str,
    code: str,
    value: Any,
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> None:
    """Resolve enum/list value to Bitrix ID(s) and set property."""
    value_for_enum = resolve_order_list_value(list_values, code, value) or value
    prop_maas_id = code_to_maas_id.get(code)
    if prop_maas_id is None:
        props[key] = value_for_enum
        return
    if isinstance(value_for_enum, list):
        enum_bids = await _resolve_enum_bitrix_ids(db, prop_maas_id, value_for_enum)
        if enum_bids:
            props[key] = enum_bids
    else:
        enum_bid = await _resolve_enum_bitrix_id(db, prop_maas_id, value_for_enum)
        if enum_bid is not None:
            props[key] = {"value": enum_bid}


def _remove_entries_for_value_ids(value_ids: list[str]) -> list[dict[str, Any]]:
    """Build array of remove objects for Bitrix: [{\"value\": {\"remove\": \"Y\"}, \"valueId\": \"...\"}, ...]."""
    return [
        {"value": {"remove": "Y"}, "valueId": str(vid)}
        for vid in value_ids
        if vid is not None
    ]


async def _build_product_properties(
    db: AsyncSession,
    order: Any,
    code_to_bitrix_id: dict[str, int],
    code_to_maas_id: dict[str, int],
    list_values: dict[str, Any],
) -> dict[str, Any]:
    """Build properties dict: key = property + Bitrix ID, value = scalar, enum ID(s), or fileData."""
    props: dict[str, Any] = {}
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
        key = _property_key(bitrix_prop_id)
        value = _order_property_value(order, spec.order_attr, spec.code)

        if spec.code == FILE_FIELD_3D_MODEL:
            if value is not None and isinstance(value, int):
                file_data = await _build_file_data_3d_model(db, value)
                if file_data:
                    props[key] = file_data
            continue
        if spec.code == FILE_FIELD_DOC:
            doc_ids = _parse_document_ids(value)
            file_data_list = (
                await _build_file_data_documents(db, doc_ids) if doc_ids else []
            )
            value_ids = product_buffer.get(key)
            if isinstance(value_ids, list) and value_ids:
                remove_entries = _remove_entries_for_value_ids(value_ids)
                props[key] = remove_entries + file_data_list
            elif file_data_list:
                props[key] = file_data_list
            continue
        if value is None:
            continue
        if spec.is_list_type:
            await _set_enum_property(
                db, props, key, spec.code, value, code_to_maas_id, list_values
            )
        else:
            _set_scalar_property(props, key, value)
    return props


async def _load_property_maps(
    db: AsyncSession, iblock_id: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Load code -> Bitrix property ID and code -> property maas_id in a single pass."""
    rows = await const_repo.product_property_list(db, iblock_id=iblock_id, limit=500)
    return await _build_property_maps_from_rows(db, rows)


def _product_base_fields(order: Any) -> dict:
    """Common scalar fields for ProductCreate/Update from order."""
    return {
        "name": getattr(order, "order_name", None) or f"Order {getattr(order, 'order_id', '')}",
        "code": getattr(order, "order_code", None),
        "length": float(x) if (x := getattr(order, "length", None)) is not None else None,
        "width": float(x) if (x := getattr(order, "width", None)) is not None else None,
        "height": float(x) if (x := getattr(order, "height", None)) is not None else None,
    }


async def order_to_product_create(db: AsyncSession, order: Any) -> ProductCreate:
    """Build ProductCreate from Order; resolves external IDs to labels, then to Bitrix enum IDs."""
    if BITRIX_PRODUCT_IBLOCK_ID <= 0:
        raise ValueError("BITRIX_PRODUCT_IBLOCK_ID must be set for product sync (config or env)")
    code_to_bitrix_id, code_to_maas_id = await _load_property_maps(db, BITRIX_PRODUCT_IBLOCK_ID)
    list_values = await fetch_list_values()
    properties = await _build_product_properties(
        db, order, code_to_bitrix_id, code_to_maas_id, list_values
    )
    return ProductCreate(
        iblockId=BITRIX_PRODUCT_IBLOCK_ID,
        **_product_base_fields(order),
        properties=properties or None,
    )


async def order_to_product_update(db: AsyncSession, order: Any) -> ProductUpdate:
    """Build ProductUpdate from Order (same property resolution as create)."""
    if BITRIX_PRODUCT_IBLOCK_ID <= 0:
        raise ValueError("BITRIX_PRODUCT_IBLOCK_ID must be set for product sync (config or env)")
    code_to_bitrix_id, code_to_maas_id = await _load_property_maps(db, BITRIX_PRODUCT_IBLOCK_ID)
    list_values = await fetch_list_values()
    properties = await _build_product_properties(
        db, order, code_to_bitrix_id, code_to_maas_id, list_values
    )
    return ProductUpdate(
        **_product_base_fields(order),
        properties=properties or None,
    )
