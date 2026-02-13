"""Product property service for catalog.productProperty.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.product_property import (
    ProductProperty,
    ProductPropertyCreate,
    ProductPropertyUpdate,
)


class ProductPropertyService:
    """CRUD for product properties."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: ProductPropertyCreate) -> int:
        """Create a product property. Returns created property ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("catalog.productProperty.add", {"fields": payload})
        return int(result.get("productProperty").get("id"))

    async def get(self, id: int) -> ProductProperty:
        """Get a product property by ID."""
        result = await self._client.call("catalog.productProperty.get", {"id": id})
        return ProductProperty.model_validate(result.get("productProperty"))

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
    ) -> list[ProductProperty]:
        """List product properties."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        result = await self._client.call("catalog.productProperty.list", params or None)
        return from_result(ProductProperty, result.get("productProperties"))

    async def update(self, id: int, fields: ProductPropertyUpdate) -> bool:
        """Update a product property."""
        payload = dump_exclude_none(fields)
        await self._client.call("catalog.productProperty.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a product property."""
        await self._client.call("catalog.productProperty.delete", {"id": id})
        return True
