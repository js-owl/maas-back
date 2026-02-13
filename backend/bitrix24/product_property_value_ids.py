"""Extract product property valueIds from Bitrix catalog.product.get response."""

import re
from typing import Any


_PROPERTY_KEY_RE = re.compile(r"^property(\d+)$")


def extract_property_value_ids(product: dict[str, Any]) -> dict[str, list[str]]:
    """Build buffer dict of property keys to list of valueIds from a product dict.

    Product from catalog.product.get may have:
    - "property258": {"value": "test", "valueId": "9816"}
    - "property259": [{"value": "test1", "valueId": "9817"}, {"value": "test2", "valueId": "9818"}]

    Returns:
        {"property258": ["9816"], "property259": ["9817", "9818"], ...}
    """
    out: dict[str, list[str]] = {}
    for key, val in (product or {}).items():
        if not _PROPERTY_KEY_RE.match(key):
            continue
        value_ids: list[str] = []
        if isinstance(val, dict) and "valueId" in val:
            v = val["valueId"]
            if v is not None:
                value_ids.append(str(v))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and "valueId" in item:
                    v = item["valueId"]
                    if v is not None:
                        value_ids.append(str(v))
        if value_ids:
            out[key] = value_ids
    return out
