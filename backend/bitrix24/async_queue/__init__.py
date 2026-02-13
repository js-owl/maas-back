"""
Async Redis-backed queue for Bitrix24 operations.

Usage:
    from backend.bitrix24.async_queue import enqueue_operation

    await enqueue_operation(
        entity_type="deal",
        action="create",
        payload={"TITLE": "New Deal"},
        local_id=42,
        redis=redis_client,
    )
"""
from backend.bitrix24.async_queue.message import (
    QueueMessage,
    deserialize_message,
    serialize_message,
    validate_message_fields,
)
from backend.bitrix24.async_queue.producer import enqueue_operation

__all__ = [
    "QueueMessage",
    "deserialize_message",
    "serialize_message",
    "validate_message_fields",
    "enqueue_operation",
]
