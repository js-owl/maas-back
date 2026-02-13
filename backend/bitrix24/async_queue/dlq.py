"""Dead-letter queue utilities."""
from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis

from backend.bitrix24.async_queue.message import QueueMessage, serialize_message
from backend.utils.logging import get_logger

logger = get_logger(__name__)

DLQ_NAME = "bitrix24:queue:dlq"


async def move_to_dlq(redis: Redis, message: QueueMessage, error: Exception) -> None:
    """Push a failed message to the dead-letter queue with metadata."""
    message.last_error = str(error)
    message.failed_at = datetime.now(timezone.utc)
    serialized = serialize_message(message)
    await redis.lpush(DLQ_NAME, serialized)
    logger.error("Moved message to DLQ: %s", serialized)


__all__ = ["DLQ_NAME", "move_to_dlq"]
