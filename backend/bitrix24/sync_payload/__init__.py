"""Sync payload layer: build Bitrix DTOs from MaaS models per docs/attribute_data_mapping.md."""

from backend.bitrix24.sync_payload.contact import (
    user_to_contact_create,
    user_to_contact_update,
)
from backend.bitrix24.sync_payload.product import (
    order_to_product_create,
    order_to_product_update,
)
from backend.bitrix24.sync_payload.deal import (
    kit_to_deal_create,
    kit_to_deal_update,
)

__all__ = [
    "user_to_contact_create",
    "user_to_contact_update",
    "order_to_product_create",
    "order_to_product_update",
    "kit_to_deal_create",
    "kit_to_deal_update",
]
