# Async Bitrix24 Queue

## Overview

The Bitrix24 async queue decouples Bitrix24 API calls from request handling by pushing operations to Redis. A background executor process consumes messages, routes them to Bitrix24 service classes, and applies retries with exponential backoff and a dead-letter queue (DLQ) for failures.

## Architecture

- **Producer**: `enqueue_operation()` serializes a `QueueMessage` and pushes it to Redis.
- **Queue**: Redis list `bitrix24:queue:default` (LPUSH/BRPOP FIFO).
- **Executor**: Dedicated process runs `executor_loop()` and dispatches operations to Bitrix24 services.
- **Idempotency**: Create operations use Redis keys to prevent duplicate entity creation.
- **Retry & DLQ**: Transient failures are retried with exponential backoff; permanent failures or exhausted attempts go to DLQ.

## Message Schema

```json
{
  "entity_type": "deal|contact|lead|invoice|product|product_row|product_property|product_property_enum|category|status|userfield",
  "action": "create|update|delete",
  "local_id": 42,
  "external_id": 123,
  "payload": { "TITLE": "Example" },
  "attempt": 0,
  "enqueued_at": "2026-02-02T12:00:00Z",
  "delay_until": "2026-02-02T12:00:10Z"
}
```

Notes:
- `local_id` is required for `create`.
- `external_id` is required for `update` and `delete`.
- `payload` contains fields for the Bitrix24 DTOs. Some entity types require additional keys:
  - `product_row`: `payload.owner_type`, `payload.owner_id`
  - `category`: `payload.entity_type_id`
  - `userfield`: `payload.entity` (deal/lead/contact)

## Queue Names

- **Default queue**: `bitrix24:queue:default`
- **Dead-letter queue**: `bitrix24:queue:dlq`
- **Idempotency key**: `bitrix24:idempotency:{entity_type}:{local_id}`

## Retry Behavior

- Base delay: **5 seconds**
- Exponential factor: **2**
- Max delay cap: **300 seconds**
- Max attempts: **5**
- `delay_until` is used to defer retries; the consumer re-enqueues messages until ready.

### Rate Limits

If Bitrix24 returns `429`, the executor applies a minimum **60s** delay and respects the `Retry-After` header if provided.

## Dead-Letter Queue (DLQ)

Messages are moved to `bitrix24:queue:dlq` when:
- The error is permanent (e.g., 4xx validation errors).
- Retry attempts are exhausted.

Each DLQ message includes:
- `last_error`: last failure message
- `failed_at`: timestamp of DLQ insertion

## Usage Examples

### Enqueue a Create Operation

```python
from backend.bitrix24.async_queue import enqueue_operation

await enqueue_operation(
    entity_type="deal",
    action="create",
    payload={"TITLE": "New Deal"},
    local_id=42,
    redis=redis_client,
)
```

### Enqueue an Update Operation

```python
await enqueue_operation(
    entity_type="deal",
    action="update",
    payload={"STAGE_ID": "WON"},
    external_id=123,
    redis=redis_client,
)
```

### Inspect and Replay DLQ

```bash
python scripts/inspect_dlq.py --limit 20
python scripts/replay_dlq.py --count 10
```
