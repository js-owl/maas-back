"""Service for crm.requisite.link.* methods."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.requisite_link import RequisiteLink, RequisiteLinkFields


class RequisiteLinkService:
    """CRUD-like operations for links between CRM objects and requisites."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def register(self, fields: RequisiteLinkFields) -> bool:
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.requisite.link.register", {"fields": payload})
        return bool(result)

    async def get(self, *, entity_type_id: int, entity_id: int) -> RequisiteLink:
        result = await self._client.call(
            "crm.requisite.link.get",
            {"entityTypeId": int(entity_type_id), "entityId": int(entity_id)},
        )
        return RequisiteLink.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[RequisiteLink]:
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.requisite.link.list", params or None)
        return from_result(RequisiteLink, result)

    async def unregister(self, *, entity_type_id: int, entity_id: int) -> bool:
        result = await self._client.call(
            "crm.requisite.link.unregister",
            {"entityTypeId": int(entity_type_id), "entityId": int(entity_id)},
        )
        return bool(result)
