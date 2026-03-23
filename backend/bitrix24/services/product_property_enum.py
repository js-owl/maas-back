"""Product property enum service for catalog.productPropertyEnum.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.product_property_enum import (
    ProductPropertyEnum,
    ProductPropertyEnumCreate,
    ProductPropertyEnumUpdate,
)


class ProductPropertyEnumService:
    """CRUD for product property enum values."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: ProductPropertyEnumCreate) -> int:
        """Create an enum value. Returns created ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("catalog.productPropertyEnum.add", {"fields": payload})
        return int(result.get("productPropertyEnum").get("id"))

    async def get(self, entity_id: int) -> ProductPropertyEnum:
        """Get an enum value by Bitrix ID."""
        result = await self._client.call("catalog.productPropertyEnum.get", {"id": entity_id})
        return ProductPropertyEnum.model_validate(result.get("productPropertyEnum"))

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[ProductPropertyEnum]:
        """List enum values (e.g. filter by propertyId)."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("catalog.productPropertyEnum.list", params or None)
        return from_result(ProductPropertyEnum, result.get("productPropertyEnums"))

    async def update(self, id: int, fields: ProductPropertyEnumUpdate) -> bool:
        """Update an enum value."""
        payload = dump_exclude_none(fields)
        await self._client.call("catalog.productPropertyEnum.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete an enum value."""
        await self._client.call("catalog.productPropertyEnum.delete", {"id": id})
        return True
