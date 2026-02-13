"""Async queue executor loop."""
from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timezone

from redis.asyncio import Redis

from backend.bitrix24.async_queue.dlq import move_to_dlq
from backend.bitrix24.async_queue.idempotency import release_idempotency_token
from backend.bitrix24.async_queue.message import QueueMessage, deserialize_message, serialize_message
from backend.bitrix24.async_queue.producer import QUEUE_NAME
from backend.bitrix24.async_queue.processor import ProcessingError, process_message
from backend.bitrix24.async_queue.retry import (
    calculate_retry_delay,
    classify_error,
    rate_limit_delay,
    retry_message,
    should_retry,
)
from backend.bitrix24.client import BitrixClient
from backend.bitrix24.exceptions import BitrixAPIError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def _setup_sigterm_handler(stop_event: asyncio.Event) -> None:
    def _handler(*_args) -> None:
        logger.info("SIGTERM received, shutting down executor loop")
        stop_event.set()

    signal.signal(signal.SIGTERM, _handler)


async def _handle_retry(
    redis: Redis,
    message: QueueMessage,
    error: Exception,
) -> None:
    error_class = classify_error(error)
    if error_class == "rate_limit" and isinstance(error, BitrixAPIError):
        delay_seconds = rate_limit_delay(error)
        logger.warning("Rate limit encountered; delaying retry for %ss", delay_seconds)
    else:
        delay_seconds = calculate_retry_delay(message.attempt)

    retry_message(message, delay_seconds)
    await redis.lpush(QUEUE_NAME, serialize_message(message))
    logger.warning(
        "Retrying message in %ss (attempt=%s): %s",
        delay_seconds,
        message.attempt,
        message.entity_type,
    )


async def executor_loop(redis: Redis, client: BitrixClient) -> None:
    """Run the executor consumer loop until SIGTERM."""
    logger.info("Starting Bitrix24 async executor loop")
    stop_event = asyncio.Event()
    _setup_sigterm_handler(stop_event)
    services_cache: dict[tuple[str, str | None], object] = {}

    while not stop_event.is_set():
        try:
            result = await redis.brpop(QUEUE_NAME, timeout=1)
        except Exception as exc:
            logger.exception("Redis BRPOP failed")
            await asyncio.sleep(1)
            continue

        if result is None:
            continue

        _, raw_message = result
        try:
            message = deserialize_message(raw_message)
        except Exception as exc:
            logger.exception("Failed to deserialize message: %s", raw_message)
            await move_to_dlq(redis, QueueMessage(entity_type="unknown", action="create"), exc)
            continue

        if message.delay_until and message.delay_until > datetime.now(timezone.utc):
            await redis.lpush(QUEUE_NAME, serialize_message(message))
            continue

        try:
            await process_message(message, client, redis, services_cache)
            logger.info(
                "Processed message: entity=%s action=%s attempt=%s",
                message.entity_type,
                message.action,
                message.attempt,
            )
        except ProcessingError as exc:
            if exc.idempotency_claimed and message.local_id is not None:
                await release_idempotency_token(
                    redis, message.entity_type, message.local_id
                )
            if should_retry(message.attempt, exc.cause):
                await _handle_retry(redis, message, exc.cause)
            else:
                await move_to_dlq(redis, message, exc.cause)
        except Exception as exc:
            if should_retry(message.attempt, exc):
                await _handle_retry(redis, message, exc)
            else:
                await move_to_dlq(redis, message, exc)

    logger.info("Executor loop stopped")


__all__ = ["executor_loop"]
