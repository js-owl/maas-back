"""Product row service for crm.item.productrow.*. Uses ownerType (entityTypeId) and ownerId."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.product_row import (
    ProductRow,
    ProductRowCreate,
    ProductRowUpdate,
)


class ProductRowService:
    """CRUD and set for product rows on CRM entities (deals, invoices)."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    def _params(self, owner_type: str, owner_id: int, **extra: Any) -> dict[str, Any]:
        return {"ownerType": owner_type, "ownerId": owner_id, **extra}

    async def add(self, fields: ProductRowCreate) -> int:
        """Add a product row. ownerType e.g. 'deal', ownerId = entity item id."""
        payload = dump_exclude_none(fields)
        result = await self._client.call(
            "crm.item.productrow.add",
            {"fields": payload},
        )
        return int(result.get("productRow").get("id"))

    async def get(self, id: int) -> ProductRow:
        """Get a product row by ID."""
        result = await self._client.call(
            "crm.item.productrow.get",
            {"id": id},
        )
        return ProductRow.model_validate(result.get("productRow"))

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        start: int | None = None,
    ) -> list[ProductRow]:
        """List product rows for the owner."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.item.productrow.list", params or None)
        return from_result(ProductRow, result.get("productRows"))

    async def update(
        self,
        id: int,
        fields: ProductRowUpdate,
    ) -> bool:
        """Update a product row."""
        payload = dump_exclude_none(fields)
        await self._client.call(
            "crm.item.productrow.update",
            {"id": id, "fields": payload},
        )
        return True

    async def delete(self, id: int) -> bool:
        """Delete a product row."""
        await self._client.call(
            "crm.item.productrow.delete",
            {"id": id},
        )
        return True

    async def set(
        self,
        owner_type: str,
        owner_id: int,
        rows: list[ProductRowCreate],
    ) -> bool:
        """Replace all product rows for the owner (crm.item.productrow.set).
        ownerType and ownerId are sent only at the top level; they are not transferred in each productRow item.
        """
        row_payloads = [dump_exclude_none(r) for r in rows]
        for p in row_payloads:
            p.pop("ownerId", None)
            p.pop("ownerType", None)
        await self._client.call(
            "crm.item.productrow.set",
            self._params(owner_type, owner_id, productRows=row_payloads),
        )
        return True
