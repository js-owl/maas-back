"""Queue message schema and serialization utilities."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueueMessage(BaseModel):
    """Schema for Bitrix24 async queue messages."""

    entity_type: str
    action: Literal["create", "update", "delete"]
    local_id: int | None = None
    external_id: int | None = None
    payload: dict[str, Any] | None = None
    attempt: int = 0
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delay_until: datetime | None = None
    last_error: str | None = None
    failed_at: datetime | None = None


def serialize_message(message: QueueMessage) -> str:
    """Serialize QueueMessage to JSON string."""
    return json.dumps(message.model_dump(mode="json"))


def deserialize_message(raw: str) -> QueueMessage:
    """Deserialize JSON string to QueueMessage."""
    data = json.loads(raw)
    return QueueMessage.model_validate(data)


def validate_message_fields(message: QueueMessage) -> None:
    """Validate required fields based on action."""
    if message.action == "create" and message.local_id is None:
        raise ValueError("local_id is required for create operations")
    if message.action in {"update", "delete"} and message.external_id is None:
        raise ValueError("external_id is required for update/delete operations")
