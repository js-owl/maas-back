from __future__ import annotations

from datetime import datetime, timezone
import json

import httpx
import pytest

from backend.auth.email_templates import render_auth_email_template
from backend.bitrix24.async_queue.idempotency import (
    check_idempotency,
    generate_idempotency_key,
)
from backend.bitrix24.async_queue.producer import enqueue_operation, QUEUE_NAME
from backend.bitrix24.async_queue.retry import (
    calculate_retry_delay,
    classify_error,
)
from backend.bitrix24.async_queue.routing import ENTITY_TYPE_ROUTING
from backend.bitrix24.auth_email_queue import activity_local_id_from_token, enqueue_auth_email
from backend.bitrix24.exceptions import BitrixAPIError


class FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.set_calls: list[tuple] = []

    async def lpush(self, queue: str, value: str) -> None:
        self.calls.append((queue, value))

    async def set(self, key: str, value: str, **kwargs) -> bool:
        self.set_calls.append((key, value, kwargs))
        return True


@pytest.mark.asyncio
async def test_enqueue_operation_requires_local_id_for_create() -> None:
    redis = FakeRedis()
    with pytest.raises(ValueError):
        await enqueue_operation(
            entity_type="deal",
            action="create",
            payload={"TITLE": "Test"},
            redis=redis,
        )


@pytest.mark.asyncio
async def test_enqueue_operation_requires_external_id_for_update() -> None:
    redis = FakeRedis()
    with pytest.raises(ValueError):
        await enqueue_operation(
            entity_type="deal",
            action="update",
            payload={"TITLE": "Test"},
            redis=redis,
        )


@pytest.mark.asyncio
async def test_enqueue_operation_pushes_message() -> None:
    redis = FakeRedis()
    await enqueue_operation(
        entity_type="deal",
        action="create",
        payload={"TITLE": "Test"},
        local_id=42,
        redis=redis,
    )

    assert len(redis.calls) == 1
    queue, raw = redis.calls[0]
    assert queue == QUEUE_NAME
    data = json.loads(raw)
    assert data["entity_type"] == "deal"
    assert data["action"] == "create"
    assert data["local_id"] == 42


@pytest.mark.asyncio
async def test_check_idempotency_sets_token() -> None:
    redis = FakeRedis()
    is_new = await check_idempotency(redis, "deal", 42)
    assert is_new is True
    assert redis.set_calls
    key, value, kwargs = redis.set_calls[0]
    assert key == generate_idempotency_key("deal", 42)
    assert kwargs["nx"] is True


def test_routing_table_contains_all_entities() -> None:
    expected = {
        "activity",
        "company",
        "deal",
        "contact",
        "lead",
        "invoice",
        "product",
        "product_row",
        "product_property",
        "product_property_enum",
        "category",
        "status",
        "userfield",
    }
    assert set(ENTITY_TYPE_ROUTING.keys()) == expected
    for entity_type, entry in ENTITY_TYPE_ROUTING.items():
        actions = entry["actions"]
        if entity_type == "activity":
            assert set(actions.keys()) == {"create"}
        elif entity_type == "company":
            assert set(actions.keys()) == {"create", "update"}
        else:
            assert set(actions.keys()) == {"create", "update", "delete"}


def test_auth_email_templates_render_common_footer_and_action_url() -> None:
    expires_at = datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc)

    confirmation = render_auth_email_template(
        "confirmation",
        action_url="https://example.com/confirm?token=abc&next=/profile",
        expires_at=expires_at,
    )
    recovery = render_auth_email_template(
        "recovery",
        action_url="https://example.com/reset?token=def",
        expires_at=expires_at,
    )

    assert "Подтвердить почту" in confirmation
    assert "Сбросить пароль" in recovery
    assert "https://example.com/confirm?token=abc&amp;next=/profile" in confirmation
    assert "https://example.com/reset?token=def" in recovery
    for html in (confirmation, recovery):
        assert "Ссылка действует до" in html
        assert "18.06.2026" in html
        assert "Никому не пересылайте ссылку" in html
        assert "{{" not in html
        assert "}}" not in html


@pytest.mark.asyncio
async def test_enqueue_auth_email_uses_token_derived_local_id() -> None:
    redis = FakeRedis()
    await enqueue_auth_email(
        redis,
        kind="confirmation",
        user_id=7,
        personal_email="user@example.com",
        token="first-token",
        url="https://example.com/confirm?token=first-token",
    )
    await enqueue_auth_email(
        redis,
        kind="confirmation",
        user_id=7,
        personal_email="user@example.com",
        token="second-token",
        url="https://example.com/confirm?token=second-token",
    )

    first = json.loads(redis.calls[0][1])
    second = json.loads(redis.calls[1][1])

    assert first["entity_type"] == "activity"
    assert first["action"] == "create"
    assert first["local_id"] == activity_local_id_from_token("first-token")
    assert second["local_id"] == activity_local_id_from_token("second-token")
    assert first["local_id"] != second["local_id"]
    assert first["payload"]["auth_email_kind"] == "confirmation"
    assert first["payload"]["user_id"] == 7


def test_retry_delay_calculation() -> None:
    assert calculate_retry_delay(0) == 5
    assert calculate_retry_delay(1) == 10
    assert calculate_retry_delay(2) == 20


def test_error_classification() -> None:
    transient = BitrixAPIError("ERR", "boom", status_code=500)
    permanent = BitrixAPIError("ERR", "boom", status_code=400)
    rate_limited = BitrixAPIError("ERR", "boom", status_code=429)
    timeout = httpx.ReadTimeout("timeout", request=httpx.Request("GET", "https://x"))

    assert classify_error(transient) == "transient"
    assert classify_error(permanent) == "permanent"
    assert classify_error(rate_limited) == "rate_limit"
    assert classify_error(timeout) == "transient"


def test_generate_idempotency_key_uniqueness() -> None:
    assert generate_idempotency_key("deal", 42) == "bitrix24:idempotency:deal:42"
    assert generate_idempotency_key("contact", 42) == "bitrix24:idempotency:contact:42"


@pytest.mark.asyncio
async def test_check_idempotency_duplicate_fails() -> None:
    class SequenceRedis(FakeRedis):
        def __init__(self) -> None:
            super().__init__()
            self.responses = [True, False]

        async def set(self, key: str, value: str, **kwargs) -> bool:
            self.set_calls.append((key, value, kwargs))
            return self.responses.pop(0)

    redis = SequenceRedis()
    assert await check_idempotency(redis, "deal", 42) is True
    assert await check_idempotency(redis, "deal", 42) is False
