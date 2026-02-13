"""Idempotency token utilities for Bitrix24 queue processing."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from redis.asyncio import Redis

IDEMPOTENCY_TTL_SECONDS = 60 * 60 * 24 * 30


def generate_idempotency_key(entity_type: str, local_id: int) -> str:
    """Generate idempotency key for entity type and local id."""
    return f"bitrix24:idempotency:{entity_type}:{local_id}"


async def check_idempotency(redis: Redis, entity_type: str, local_id: int) -> bool:
    """Check idempotency using SET NX. Returns True if new token created."""
    key = generate_idempotency_key(entity_type, local_id)
    return bool(await redis.set(key, "pending", nx=True, ex=IDEMPOTENCY_TTL_SECONDS))


async def store_idempotency_token(
    redis: Redis,
    entity_type: str,
    local_id: int,
    bitrix24_id: int | str,
) -> None:
    """Store idempotency token value with Bitrix24 ID and created timestamp."""
    key = generate_idempotency_key(entity_type, local_id)
    payload = json.dumps({
        "bitrix24_id": bitrix24_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await redis.set(key, payload, ex=IDEMPOTENCY_TTL_SECONDS)


async def release_idempotency_token(redis: Redis, entity_type: str, local_id: int) -> None:
    """Remove a pending idempotency token (e.g., after failed create)."""
    key = generate_idempotency_key(entity_type, local_id)
    await redis.delete(key)


__all__ = [
    "IDEMPOTENCY_TTL_SECONDS",
    "generate_idempotency_key",
    "check_idempotency",
    "store_idempotency_token",
    "release_idempotency_token",
]
