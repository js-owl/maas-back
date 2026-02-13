"""
Resolve external IDs from orders/kits to display values (labels) per docs/attribute_data_mapping.md.

Orders and kits store external IDs (or arrays) that refer to lists from the calculator service.
Bitrix enumerations expect labels, so we resolve id → label (or russian_name for locations)
before matching to Bitrix enums.
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

LIST_KEYS = (
    "materials",
    "services",
    "tolerance",
    "finish",
    "cover",
    "control_types",
    "cert_costs",
    "locations",
)


async def _fetch_safe(
    fetch_fn: Callable,
    set_result: Callable[[dict, Any], None],
    result: dict,
    log_name: str,
) -> None:
    """Run fetch_fn and set result; log warning on failure."""
    try:
        data = await fetch_fn()
        set_result(result, data)
    except Exception as e:
        logger.warning("Failed to fetch %s for external list resolution: %s", log_name, e)


async def fetch_list_values() -> dict[str, Any]:
    """Fetch all external list values from the calculator service."""
    result = {k: [] for k in LIST_KEYS}

    await _fetch_safe(
        get_materials,
        lambda r, d: r.__setitem__("materials", (d.get("materials") or []) if isinstance(d, dict) else []),
        result,
        "materials",
    )
    await _fetch_safe(
        get_all_services,
        lambda r, d: r.__setitem__("services", d.get("services") if isinstance(d, dict) else []),
        result,
        "services",
    )
    def set_coefficients(r: dict, d: Any) -> None:
        if not isinstance(d, dict):
            return
        for key in ("tolerance", "finish", "cover", "control_types", "cert_costs"):
            r[key] = d.get(key) or []
    await _fetch_safe(get_coefficients, set_coefficients, result, "coefficients")
    await _fetch_safe(
        get_locations,
        lambda r, d: r.__setitem__("locations", (d.get("locations") or []) if isinstance(d, dict) else []),
        result,
        "locations",
    )

    return result


def _id_to_label(items: list, external_id: Any, label_key: str = "label") -> str | None:
    """Find item by id; return label_key value. Items may be dicts or strings."""
    if external_id is None:
        return None
    sid = str(external_id).strip()
    for item in items:
        if isinstance(item, dict):
            item_id = item.get("id")
            if item_id is not None and str(item_id).strip() == sid:
                return item.get(label_key) or str(item_id)
        elif str(item).strip() == sid:
            return str(item)
    return None


def _ids_to_labels(items: list, external_ids: list, label_key: str = "label") -> list[str]:
    """Resolve each external id to label; return list (skip unresolved)."""
    out = []
    for eid in external_ids:
        label = _id_to_label(items, eid, label_key)
        if label is not None:
            out.append(label)
    return out


def _single_or_many(
    items: list,
    external_id: Any,
    label_key: str = "label",
) -> str | list[str] | None:
    """Resolve single id or list of ids to label(s). Returns list when input is list."""
    if external_id is None:
        return None
    if isinstance(external_id, list):
        if not external_id:
            return None
        return _ids_to_labels(items, external_id, label_key)
    return _id_to_label(items, external_id, label_key)


# Resolvers by product/deal field (code or key)
def resolve_material_label(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("materials") or [], external_id)


def resolve_service_label(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("services") or [], external_id)


def resolve_tolerance_label(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("tolerance") or [], external_id)


def resolve_finish_label(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("finish") or [], external_id)


def resolve_cover_label(data: dict[str, Any], external_id: Any) -> str | list[str] | None:
    return _single_or_many(data.get("cover") or [], external_id)


def resolve_control_type_label(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("control_types") or [], external_id)


def resolve_cert_label(data: dict[str, Any], external_id: Any) -> str | list[str] | None:
    return _single_or_many(data.get("cert_costs") or [], external_id)


def resolve_location_russian_name(data: dict[str, Any], external_id: Any) -> str | None:
    return _id_to_label(data.get("locations") or [], external_id)


_CODE_RESOLVERS: dict[str, Callable[[dict, Any], str | list[str] | None]] = {
    "UP_CAT_MATERIAL": resolve_material_label,
    "UP_CAT_SERVICE": resolve_service_label,
    "UP_CAT_ACCURACY": resolve_tolerance_label,
    "UP_CAT_ROUGHNESS": resolve_finish_label,
    "UP_CAT_FINISHING": resolve_cover_label,
    "UP_CAT_CONTROL": resolve_control_type_label,
    "UP_CAT_CERTIFICATES": resolve_cert_label,
}


def resolve_order_list_value(
    data: dict[str, Any], code: str, raw_value: Any
) -> str | list[str] | None:
    """Resolve order list-type field (id or array of ids) to label(s) for Bitrix enum matching."""
    if raw_value is None:
        return None
    resolver = _CODE_RESOLVERS.get(code)
    if resolver is not None:
        return resolver(data, raw_value)
    if isinstance(raw_value, list):
        return [str(v).strip() for v in raw_value if v is not None]
    return str(raw_value).strip() if raw_value is not None else None
