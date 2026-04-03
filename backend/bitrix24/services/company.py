"""Company service for crm.company.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.company import Company, CompanyCreate, CompanyUpdate


class CompanyService:
    """CRUD for CRM companies."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: CompanyCreate) -> int:
        """Create a company. Returns created company ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.company.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Company:
        """Get a company by ID."""
        result = await self._client.call("crm.company.get", {"id": id})
        return Company.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Company]:
        """List companies with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.company.list", params or None)
        return from_result(Company, result)

    async def update(self, id: int, fields: CompanyUpdate) -> bool:
        """Update a company."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.company.update", {"id": id, "fields": payload})
        return True
