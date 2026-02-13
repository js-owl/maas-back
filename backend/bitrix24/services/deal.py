"""Deal service for crm.deal.* and crm.item.delete."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.constants import EntityTypeId
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.deal import Deal, DealCreate, DealUpdate


class DealService:
    """CRUD for deals via crm.deal.* and crm.item.delete."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    def _deal_fields(self, fields: DealCreate | DealUpdate) -> dict[str, Any]:
        """Build fields dict for add/update, merging userfields (UF_CRM_*) into the payload."""
        payload = dump_exclude_none(fields)
        payload.pop("userfields", None)
        if getattr(fields, "userfields", None):
            payload.update(fields.userfields)
        return payload

    async def add(self, fields: DealCreate) -> int:
        """Create a deal. Returns created deal ID. Use fields.userfields for UF_CRM_* fields."""
        payload = self._deal_fields(fields)
        result = await self._client.call("crm.deal.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Deal:
        """Get a deal by ID."""
        result = await self._client.call("crm.deal.get", {"id": id})
        return Deal.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Deal]:
        """List deals with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.deal.list", params or None)
        return from_result(Deal, result)

    async def update(self, id: int, fields: DealUpdate) -> bool:
        """Update a deal. Returns True on success. Use fields.userfields for UF_CRM_* fields."""
        payload = self._deal_fields(fields)
        await self._client.call("crm.deal.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a deal. Uses crm.deal.delete."""
        await self._client.call("crm.deal.delete", {"id": id})
        return True
