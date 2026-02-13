"""Product service for catalog.product.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.product import Product, ProductCreate, ProductUpdate


class ProductService:
    """CRUD for catalog products."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    def _product_fields(self, fields: ProductCreate | ProductUpdate) -> dict[str, Any]:
        """Build fields dict for add/update, merging product properties into the payload."""
        payload = dump_exclude_none(fields)
        payload.pop("properties", None)
        if getattr(fields, "properties", None):
            payload.update(fields.properties)
        return payload

    async def add(self, fields: ProductCreate) -> int:
        """Create a product. Returns created product ID. Use fields.properties for product properties."""
        payload = self._product_fields(fields)
        result = await self._client.call("catalog.product.add", {"fields": payload})
        return int(result.get("element").get("id"))

    async def get(self, id: int) -> Product:
        """Get a product by ID."""
        result = await self._client.call("catalog.product.get", {"id": id})
        return Product.model_validate(result.get("product"))

    async def get_raw(self, id: int) -> dict[str, Any]:
        """Get raw product dict by ID (includes property* keys with value/valueId)."""
        result = await self._client.call("catalog.product.get", {"id": id})
        product = result.get("product")
        return product if isinstance(product, dict) else {}

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Product]:
        """List products with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("catalog.product.list", params or None)
        return from_result(Product, result.get("products"))

    async def update(self, id: int, fields: ProductUpdate) -> bool:
        """Update a product. Use fields.properties for product properties."""
        payload = self._product_fields(fields)
        await self._client.call("catalog.product.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete a product."""
        await self._client.call("catalog.product.delete", {"id": id})
        return True
