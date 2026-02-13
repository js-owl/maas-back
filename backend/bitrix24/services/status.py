"""Status service for crm.status.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.status import Status, StatusCreate, StatusUpdate


class StatusService:
    """CRUD and entity discovery for CRM status entities (deal stages, sources, types)."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: StatusCreate) -> int:
        """Create a status. Returns created status ID (ENTITY_ID:STATUS_ID)."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.status.add", {"fields": payload})
        return int(result)

    async def list(self, filter: dict[str, Any] | None = None) -> list[Status]:
        """List statuses with optional filter (e.g. ENTITY_ID)."""
        params = {"filter": filter} if filter else {}
        result = await self._client.call("crm.status.list", params or None)
        return from_result(Status, result)

    async def update(self, id: int, fields: StatusUpdate) -> bool:
        """Update a status by list item id."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.status.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a status by list item id."""
        await self._client.call("crm.status.delete", {"id": id})
        return True

    async def entity_types(self) -> list[dict[str, Any]]:
        """Get supported entity types (crm.status.entity.types)."""
        result = await self._client.call("crm.status.entity.types")
        return result if isinstance(result, list) else [result]

    async def entity_items(self, entity_id: str) -> list[dict[str, Any]]:
        """Get entity items sorted by SORT (crm.status.entity.items)."""
        result = await self._client.call("crm.status.entity.items", {"entityId": entity_id})
        return result if isinstance(result, list) else [result]
