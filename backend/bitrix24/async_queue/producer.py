"""Queue producer utilities for Bitrix24 async operations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from redis.asyncio import Redis

from backend.bitrix24.async_queue.message import (
    QueueMessage,
    serialize_message,
    validate_message_fields,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)

QUEUE_NAME = "bitrix24:queue:default"


async def enqueue_operation(
    entity_type: str,
    action: Literal["create", "update", "delete"],
    payload: dict[str, Any] | None,
    *,
    local_id: int | None = None,
    external_id: int | None = None,
    redis: Redis,
) -> None:
    """Enqueue a Bitrix24 operation for background processing."""
    if not entity_type:
        raise ValueError("entity_type is required")
    if action not in {"create", "update", "delete"}:
        raise ValueError("action must be one of: create, update, delete")

    message = QueueMessage(
        entity_type=entity_type,
        action=action,
        local_id=local_id,
        external_id=external_id,
        payload=payload,
        attempt=0,
        enqueued_at=datetime.now(timezone.utc),
    )
    validate_message_fields(message)
    serialized = serialize_message(message)

    try:
        await redis.lpush(QUEUE_NAME, serialized)
        logger.info(
            "Enqueued Bitrix24 operation: entity=%s action=%s",
            entity_type,
            action,
        )
    except Exception as exc:
        logger.exception("Failed to enqueue Bitrix24 operation")
        raise exc
