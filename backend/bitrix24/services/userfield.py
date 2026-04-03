"""Userfield service for crm.{entity}.userfield.*. Scoped by entity: deal, lead, contact, company."""

from __future__ import annotations

from typing import Any, Literal

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.userfield import Userfield, UserfieldCreate, UserfieldUpdate

EntityName = Literal["deal", "lead", "contact", "company"]


class UserfieldService:
    """CRUD for user-defined fields. Entity name determines crm.{entity}.userfield.*."""

    def __init__(self, client: BitrixClient, entity: EntityName) -> None:
        self._client = client
        self._entity = entity
        self._prefix = f"crm.{entity}.userfield"

    async def add(self, fields: UserfieldCreate) -> int:
        """Create a userfield. Returns created field info."""
        payload = dump_exclude_none(fields)
        result = await self._client.call(f"{self._prefix}.add", {"fields": payload})
        return int(result)

    async def get(self, id: str) -> Userfield:
        """Get a userfield by ID."""
        result = await self._client.call(f"{self._prefix}.get", {"id": id})
        return Userfield.model_validate(result)

    async def list(self, filter: dict[str, Any] | None = None) -> list[Userfield]:
        """List userfields with optional filter."""
        params = {"filter": filter} if filter else {}
        result = await self._client.call(f"{self._prefix}.list", params or None)
        return from_result(Userfield, result)

    async def update(self, id: str, fields: UserfieldUpdate) -> bool:
        """Update a userfield."""
        payload = dump_exclude_none(fields)
        await self._client.call(f"{self._prefix}.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: str) -> bool:
        """Delete a userfield."""
        await self._client.call(f"{self._prefix}.delete", {"id": id})
        return True
