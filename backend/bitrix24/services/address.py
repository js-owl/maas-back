"""Address service for crm.address.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.address import Address, AddressUpsert


class AddressService:
    """CRUD-like operations for requisite addresses."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: AddressUpsert) -> bool:
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.address.add", {"fields": payload})
        return bool(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Address]:
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.address.list", params or None)
        return from_result(Address, result)

    async def update(self, fields: AddressUpsert) -> bool:
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.address.update", {"fields": payload})
        return bool(result)

    async def delete(self, fields: AddressUpsert) -> bool:
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.address.delete", {"fields": payload})
        return bool(result)
