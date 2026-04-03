"""Bank detail service for crm.requisite.bankdetail.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.bank_detail import BankDetail, BankDetailCreate, BankDetailUpdate


class BankDetailService:
    """CRUD for requisite bank details."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: BankDetailCreate) -> int:
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.requisite.bankdetail.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> BankDetail:
        result = await self._client.call("crm.requisite.bankdetail.get", {"id": id})
        return BankDetail.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[BankDetail]:
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.requisite.bankdetail.list", params or None)
        return from_result(BankDetail, result)

    async def update(self, id: int, fields: BankDetailUpdate) -> bool:
        payload = dump_exclude_none(fields)
        await self._client.call("crm.requisite.bankdetail.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        await self._client.call("crm.requisite.bankdetail.delete", {"id": id})
        return True
