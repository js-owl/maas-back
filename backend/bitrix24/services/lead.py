"""Lead service for crm.lead.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.lead import Lead, LeadCreate, LeadUpdate


class LeadService:
    """CRUD for CRM leads."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: LeadCreate) -> int:
        """Create a lead. Returns created lead ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.lead.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Lead:
        """Get a lead by ID."""
        result = await self._client.call("crm.lead.get", {"id": id})
        return Lead.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Lead]:
        """List leads with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.lead.list", params or None)
        return from_result(Lead, result)

    async def update(self, id: int, fields: LeadUpdate) -> bool:
        """Update a lead."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.lead.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a lead."""
        await self._client.call("crm.lead.delete", {"id": id})
        return True
