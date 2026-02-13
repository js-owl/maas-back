"""Invoice service for crm.invoice.*."""

from __future__ import annotations

from typing import Any

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.invoice import Invoice, InvoiceCreate, InvoiceUpdate


class InvoiceService:
    """CRUD for CRM invoices."""

    def __init__(self, client: BitrixClient) -> None:
        self._client = client

    async def add(self, fields: InvoiceCreate) -> int:
        """Create an invoice. Returns created invoice ID."""
        payload = dump_exclude_none(fields)
        result = await self._client.call("crm.invoice.add", {"fields": payload})
        return int(result)

    async def get(self, id: int) -> Invoice:
        """Get an invoice by ID."""
        result = await self._client.call("crm.invoice.get", {"id": id})
        return Invoice.model_validate(result)

    async def list(
        self,
        *,
        filter: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        select: list[str] | None = None,
        start: int | None = None,
    ) -> list[Invoice]:
        """List invoices with optional filter, order, select, start."""
        params: dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if order is not None:
            params["order"] = order
        if select is not None:
            params["select"] = select
        if start is not None:
            params["start"] = start
        result = await self._client.call("crm.invoice.list", params or None)
        return from_result(Invoice, result)

    async def update(self, id: int, fields: InvoiceUpdate) -> bool:
        """Update an invoice."""
        payload = dump_exclude_none(fields)
        await self._client.call("crm.invoice.update", {"id": id, "fields": payload})
        return True

    async def delete(self, id: int) -> bool:
        """Delete an invoice."""
        await self._client.call("crm.invoice.delete", {"id": id})
        return True
