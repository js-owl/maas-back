"""Async Bitrix CRM smart-process helper for materials/prices."""

from __future__ import annotations

import re
from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixCrmType:
    """Loads a CRM smart-process type by title (materials / prices)."""

    def __init__(self, client: BitrixClient, title: str) -> None:
        self.client = client
        self.title = title
        self.id: int = -1
        self.entity_type_id: int = -1
        self.prefix: str = ""
        self.fields: dict[str, Any] = {}
        self.items_list: list[dict[str, Any]] = []
        self.params: dict[str, Any] = {}

    async def update(self) -> BitrixCrmType:
        await self._get_id()
        if self.id < 0:
            raise ValueError(f"Bitrix CRM type not found: {self.title}")
        await self._get_params()
        await self._get_fields()
        await self._get_items()
        return self

    async def _get_id(self) -> None:
        self.id = -1
        self.entity_type_id = -1
        result = await self.client.call("crm.type.list")
        types = (result or {}).get("types", []) if isinstance(result, dict) else []
        for crm_obj in types:
            if crm_obj.get("title", "") == self.title:
                self.id = int(crm_obj["id"])
                self.entity_type_id = int(crm_obj["entityTypeId"])
                self.prefix = f"ufCrm{self.id}"
                break

    async def _get_params(self) -> None:
        result = await self.client.call("crm.type.get", {"id": self.id})
        self.params = (result or {}).get("type", {}) if isinstance(result, dict) else {}

    async def _get_userfieldconfig(self, field_name: str) -> dict[str, Any]:
        result = await self.client.call(
            "userfieldconfig.list",
            {
                "moduleId": "crm",
                "select": {"0": "*"},
                "filter": {"fieldName": field_name},
                "start": "0",
            },
        )
        if not isinstance(result, dict):
            return {}
        fields = result.get("fields") or []
        # total may be outside result depending on Bitrix; tolerate 0/1
        if len(fields) == 1:
            return fields[0]
        return {}

    async def _get_fields(self) -> None:
        result = await self.client.call(
            "crm.item.fields", {"entityTypeId": self.entity_type_id}
        )
        fields = (result or {}).get("fields", {}) if isinstance(result, dict) else {}
        self.fields = fields
        for field_id, meta in list(self.fields.items()):
            if re.match(r"^ufCrm", field_id):
                upper = meta.get("upperName", "")
                if upper:
                    extra = await self._get_userfieldconfig(upper)
                    if extra:
                        self.fields[field_id].update(extra)

    async def _get_items(self) -> None:
        start = 0
        items: list[dict[str, Any]] = []
        while True:
            data = await self.client.call_full(
                "crm.item.list",
                {
                    "entityTypeId": self.entity_type_id,
                    "start": start,
                    "useOriginalUfNames": "N",
                },
            )
            result = data.get("result") or {}
            if isinstance(result, dict):
                items.extend(result.get("items") or [])
            start = int(data.get("next") or 0)
            if start == 0:
                break
        self.items_list = items

    async def item_update(self, item_id: int, fields: dict[str, Any]) -> None:
        await self.client.call(
            "crm.item.update",
            {
                "entityTypeId": self.entity_type_id,
                "id": item_id,
                "fields": fields,
                "useOriginalUfNames": "N",
            },
        )


def get_enum_dict(crm: BitrixCrmType, field_name: str) -> dict[str, str]:
    """Return enum ID → VALUE for a CRM userfield short name."""
    field_settings = crm.fields.get(crm.prefix + field_name, {})
    enum_list = field_settings.get("items") or []
    res: dict[str, str] = {}
    for entry in enum_list:
        if "ID" in entry:
            res[str(entry["ID"])] = str(entry.get("VALUE", ""))
    return res


def parse_money(value: Any) -> float:
    """Parse Bitrix money field (e.g. '123.45|RUB') to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    if "|" in text:
        text = text.split("|", 1)[0]
    text = text.replace(",", ".").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_money(amount: float, currency: str = "RUB") -> str:
    return f"{round(amount, 2)}|{currency}"
