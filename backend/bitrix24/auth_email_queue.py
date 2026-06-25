"""Queue helpers for Bitrix24-authored authentication emails."""

from __future__ import annotations

import zlib
from typing import Literal

from redis.asyncio import Redis

from backend.bitrix24.async_queue import enqueue_operation

AuthEmailKind = Literal["confirmation", "recovery"]


def activity_local_id_from_token(token: str) -> int:
    """Derive a stable positive queue local_id from a one-time auth token."""
    return zlib.crc32(token.encode("utf-8")) & 0x7FFFFFFF


async def enqueue_auth_email(
    redis: Redis,
    *,
    kind: AuthEmailKind,
    user_id: int,
    personal_email: str,
    token: str,
    url: str,
) -> None:
    await enqueue_operation(
        entity_type="activity",
        action="create",
        payload={
            "auth_email_kind": kind,
            "user_id": user_id,
            "personal_email": personal_email,
            "url": url,
        },
        local_id=activity_local_id_from_token(token),
        redis=redis,
    )
