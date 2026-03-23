"""
Resolve external IDs from orders/kits to display values (labels) per docs/attribute_data_mapping.md.

Orders and kits store external IDs (or arrays) that refer to lists from the calculator service.
Bitrix enumerations expect labels, so we resolve external_id → label before matching to Bitrix enums.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.calculations.proxy import (
    get_all_services,
    get_coefficients,
    get_locations,
    get_materials,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)

# Keys in the list_values dict returned by fetch_list_values()
LIST_VALUE_KEYS = (
    "materials",
    "services",
    "tolerance",
    "finish",
    "cover",
    "control_types",
    "cert_costs",
    "locations",
)


async def _fetch_list_and_merge(
    result: dict[str, Any],
    fetch_fn: Callable[[], Any],
    result_key: str | tuple[str, ...],
    source_key: str | None = None,
    log_name: str = "",
) -> None:
    """Call fetch_fn, merge response into result; log warning on failure."""
    try:
        data = await fetch_fn()
        if isinstance(result_key, str):
            if isinstance(data, list):
                result[result_key] = data
            elif isinstance(data, dict):
                result[result_key] = data.get(source_key or result_key) or []
            else:
                result[result_key] = []
        elif isinstance(result_key, tuple) and isinstance(data, dict):
            for key in result_key:
                result[key] = data.get(key) or []
        else:
            return
    except Exception as e:
        logger.warning(
            "Failed to fetch %s for external list resolution: %s",
            log_name or result_key,
            e,
        )


async def fetch_list_values() -> dict[str, Any]:
    """Fetch all external list values from the calculator service."""
    list_values: dict[str, Any] = {k: [] for k in LIST_VALUE_KEYS}

    await _fetch_list_and_merge(
        list_values, get_materials, "materials", "materials", "materials"
    )
    await _fetch_list_and_merge(
        list_values, get_all_services, "services", "services", "services"
    )
    await _fetch_list_and_merge(
        list_values,
        get_coefficients,
        ("tolerance", "finish", "cover", "control_types", "cert_costs"),
        None,
        "coefficients",
    )
    await _fetch_list_and_merge(
        list_values, get_locations, "locations", "locations", "locations"
    )

    return list_values


# --- External ID → label (Order/Kit → Bitrix) ---


def _external_id_to_label(
    items: list[Any],
    external_id: Any,
    label_key: str = "label",
    id_key: str = "id",
) -> str | None:
    """Find item by id; return its label. Items may be dicts or strings."""
    if external_id is None:
        return None
    search_id = str(external_id).strip()
    for item in items:
        if isinstance(item, dict):
            item_id = item.get(id_key)
            if item_id is not None and str(item_id).strip() == search_id:
                return item.get(label_key) or str(item_id)
        elif str(item).strip() == search_id:
            return str(item)
    return None


def _external_ids_to_labels(
    items: list[Any],
    external_ids: list[Any],
    label_key: str = "label",
    id_key: str = "id",
) -> list[str]:
    """Resolve each external id to label; skip unresolved."""
    labels: list[str] = []
    for ext_id in external_ids:
        label = _external_id_to_label(items, ext_id, label_key, id_key)
        if label is not None:
            labels.append(label)
    return labels


def _resolve_external_id_or_list_to_labels(
    items: list[Any],
    external_id: Any,
    label_key: str = "label",
    id_key: str = "id",
) -> str | list[str] | None:
    """Resolve a single external id or list of ids to label(s). Returns list when input is list."""
    if external_id is None:
        return None
    if isinstance(external_id, list):
        if not external_id:
            return None
        return _external_ids_to_labels(items, external_id, label_key, id_key)
    return _external_id_to_label(items, external_id, label_key, id_key)


def resolve_material_label(list_values: dict[str, Any], external_id: Any) -> str | None:
    return _external_id_to_label(list_values.get("materials") or [], external_id)


def resolve_service_label(list_values: dict[str, Any], external_id: Any) -> str | None:
    return _external_id_to_label(list_values.get("services") or [], external_id)


def resolve_tolerance_label(list_values: dict[str, Any], external_id: Any) -> str | None:
    return _external_id_to_label(list_values.get("tolerance") or [], external_id)


def resolve_finish_label(list_values: dict[str, Any], external_id: Any) -> str | None:
    return _external_id_to_label(list_values.get("finish") or [], external_id)


def resolve_cover_label(
    list_values: dict[str, Any], external_id: Any
) -> str | list[str] | None:
    return _resolve_external_id_or_list_to_labels(
        list_values.get("cover") or [], external_id
    )


def resolve_control_type_label(
    list_values: dict[str, Any], external_id: Any
) -> str | None:
    return _external_id_to_label(
        list_values.get("control_types") or [], external_id, id_key="value"
    )


def resolve_cert_label(
    list_values: dict[str, Any], external_id: Any
) -> str | list[str] | None:
    return _resolve_external_id_or_list_to_labels(
        list_values.get("cert_costs") or [], external_id
    )


def resolve_location_label(
    list_values: dict[str, Any], external_id: Any
) -> str | None:
    return _external_id_to_label(list_values.get("locations") or [], external_id)


# Product property code → resolver (external id → label for Order → Bitrix)
_CODE_TO_LABEL_RESOLVERS: dict[
    str, Callable[[dict[str, Any], Any], str | list[str] | None]
] = {
    "UP_CAT_MATERIAL": resolve_material_label,
    "UP_CAT_SERVICE": resolve_service_label,
    "UP_CAT_ACCURACY": resolve_tolerance_label,
    "UP_CAT_ROUGHNESS": resolve_finish_label,
    "UP_CAT_FINISHING": resolve_cover_label,
    "UP_CAT_CONTROL": resolve_control_type_label,
    "UP_CAT_CERTIFICATES": resolve_cert_label,
}


def resolve_order_list_value(
    list_values: dict[str, Any], property_code: str, raw_value: Any
) -> str | list[str] | None:
    """Resolve order list-type field (external id or list of ids) to label(s) for Bitrix enum matching."""
    if raw_value is None:
        return None
    resolver = _CODE_TO_LABEL_RESOLVERS.get(property_code)
    if resolver is not None:
        return resolver(list_values, raw_value)
    if isinstance(raw_value, list):
        return [str(v).strip() for v in raw_value if v is not None]
    return str(raw_value).strip() if raw_value is not None else None


# --- Label → external ID (Bitrix → Order/Kit) ---


def _label_to_external_id(
    items: list[Any],
    label: Any,
    label_key: str = "label",
    id_key: str = "id",
) -> str | None:
    """Find item by label; return its external id. Reverse of _external_id_to_label."""
    if label is None or (isinstance(label, str) and not label.strip()):
        return None
    search_label = str(label).strip()
    for item in items:
        if isinstance(item, dict):
            item_label = item.get(label_key) or item.get(id_key)
            if item_label is not None and str(item_label).strip() == search_label:
                raw_id = item.get(id_key)
                return str(raw_id).strip() if raw_id is not None else None
        elif str(item).strip() == search_label:
            return str(item)
    return None


def _labels_to_external_ids(
    items: list[Any],
    labels: list[Any],
    label_key: str = "label",
    id_key: str = "id",
) -> list[str]:
    """Resolve each label to external id; skip unresolved. Reverse of _external_ids_to_labels."""
    external_ids: list[str] = []
    for lbl in labels:
        ext_id = _label_to_external_id(items, lbl, label_key, id_key)
        if ext_id is not None:
            external_ids.append(ext_id)
    return external_ids


def _resolve_label_or_list_to_external_ids(
    items: list[Any],
    label: Any,
    label_key: str = "label",
    id_key: str = "id",
) -> str | list[str] | None:
    """Resolve a single label or list of labels to external id(s). Returns list when input is list."""
    if label is None:
        return None
    if isinstance(label, list):
        if not label:
            return None
        return _labels_to_external_ids(items, label, label_key, id_key)
    return _label_to_external_id(items, label, label_key, id_key)


def resolve_material_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    return _label_to_external_id(list_values.get("materials") or [], label)


def resolve_service_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    return _label_to_external_id(list_values.get("services") or [], label)


def resolve_tolerance_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    return _label_to_external_id(list_values.get("tolerance") or [], label)


def resolve_finish_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    return _label_to_external_id(list_values.get("finish") or [], label)


def resolve_cover_external_id(
    list_values: dict[str, Any], label: Any
) -> str | list[str] | None:
    return _resolve_label_or_list_to_external_ids(
        list_values.get("cover") or [], label
    )


def resolve_control_type_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    return _label_to_external_id(
        list_values.get("control_types") or [], label, id_key="value"
    )


def resolve_cert_external_id(
    list_values: dict[str, Any], label: Any
) -> str | list[str] | None:
    return _resolve_label_or_list_to_external_ids(
        list_values.get("cert_costs") or [], label
    )


def resolve_location_external_id(
    list_values: dict[str, Any], label: Any
) -> str | None:
    """Resolve location label to external id. Reverse of resolve_location_label."""
    return _label_to_external_id(list_values.get("locations") or [], label)


# Product property code → resolver (label → external id for Bitrix → Order)
_CODE_TO_EXTERNAL_ID_RESOLVERS: dict[
    str, Callable[[dict[str, Any], Any], str | list[str] | None]
] = {
    "UP_CAT_MATERIAL": resolve_material_external_id,
    "UP_CAT_SERVICE": resolve_service_external_id,
    "UP_CAT_ACCURACY": resolve_tolerance_external_id,
    "UP_CAT_ROUGHNESS": resolve_finish_external_id,
    "UP_CAT_FINISHING": resolve_cover_external_id,
    "UP_CAT_CONTROL": resolve_control_type_external_id,
    "UP_CAT_CERTIFICATES": resolve_cert_external_id,
}


def resolve_product_list_value_to_external_id(
    list_values: dict[str, Any], property_code: str, raw_value: Any
) -> str | list[str] | None:
    """Resolve product list-type field (label or list of labels from Bitrix) to external id(s) for Order."""
    if raw_value is None:
        return None
    resolver = _CODE_TO_EXTERNAL_ID_RESOLVERS.get(property_code)
    if resolver is not None:
        return resolver(list_values, raw_value)
    if isinstance(raw_value, list):
        return [str(v).strip() for v in raw_value if v is not None]
    return str(raw_value).strip() if raw_value is not None else None
