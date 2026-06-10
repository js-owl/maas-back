"""Activity service for crm.activity.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.activity import Activity, ActivityCreate, ActivityUpdate


class ActivityService:
    """CRUD for CRM activities."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: ActivityCreate) -> int:
        """Create an activity. Returns created activity ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.activity.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Activity:
        """Get an activity by ID (includes extra fields in model)."""
        result = await self._client.call("crm.activity.get", {"id": id})
        return Activity.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Activity]:
        """List activities with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.activity.list", params or None)
        return from_result(Activity, result)

    async def update(self, id: int, fields: ActivityUpdate) -> bool:
        """Update an activity."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.activity.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete an activity."""
        await self._client.call("crm.activity.delete", {"id": id})
        return True
