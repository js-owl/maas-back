"""Contact service for crm.contact.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.contact import Contact, ContactCreate, ContactUpdate


class ContactService:
    """CRUD for CRM contacts."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: ContactCreate) -> int:
        """Create a contact. Returns created contact ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.contact.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Contact:
        """Get a contact by ID."""
        result = await self._client.call("crm.contact.get", {"id": id})
        return Contact.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Contact]:
        """List contacts with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.contact.list", params or None)
        return from_result(Contact, result)

    async def update(self, id: int, fields: ContactUpdate) -> bool:
        """Update a contact."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.contact.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a contact."""
        await self._client.call("crm.contact.delete", {"id": id})
        return True
