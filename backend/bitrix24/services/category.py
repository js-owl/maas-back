"""Category (sales funnel) service for crm.category.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.category import Category, CategoryCreate, CategoryUpdate


class CategoryService:
    """CRUD for sales funnel (category) entities. entityTypeId=2 for deals."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, entity_type_id: int, fields: CategoryCreate) -> int:
        """Create a category. Returns created category with id."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.category.add", {
            "entityTypeId": entity_type_id,
            "fields": payload,
        })
        return int(result.get("category").get("id"))

    async def get(self, entity_type_id: int, id: int) -> Category:
        """Get a category by ID."""
        result = await self._client.call("crm.category.get", {
            "entityTypeId": entity_type_id,
            "id": id,
        })
        return Category.model_validate(result.get("category"))

    async def list(self, entity_type_id: int) -> list[Category]:
        """List categories for the entity type."""
        result = await self._client.call("crm.category.list", {"entityTypeId": entity_type_id})
        return from_result(Category, result.get("categories"))

    async def update(self, entity_type_id: int, id: int, fields: CategoryUpdate) -> bool:
        """Update a category."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.category.update", {
            "entityTypeId": entity_type_id,
            "id": id,
            "fields": payload,
        })
        return True

    async def delete(self, entity_type_id: int, id: int) -> bool:
        """Delete a category."""
        await self._client.call("crm.category.delete", {
            "entityTypeId": entity_type_id,
            "id": id,
        })
        return True
