# `POST /kits/{kit_id}/confirm` — Kit Confirmation

## Purpose

Confirms a kit and synchronises it with Bitrix24 for the first time. This is the explicit step that transitions a kit from draft state (`AWAITING_CONFIRMATION`) into the active CRM pipeline (`NEW`). All orders belonging to the kit are pushed to Bitrix24 as **Products**, and the kit itself is pushed as a **Deal**.

---

## Authentication

Requires a valid user session. The requesting user must own the kit, or be an admin.

---

## Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `kit_id` | `integer` | ID of the kit to confirm |

---

## Preconditions

All of the following must be true before the route proceeds:

1. **Kit exists** — a kit with the given `kit_id` must be found in the database.
2. **Ownership** — the requesting user must own the kit or have admin rights.
3. **Status is `AWAITING_CONFIRMATION`** — the kit must be in exactly this status. Any other status (e.g. `NEW`, `PREPARATION`) causes an immediate `400` error. This guard prevents accidental re-confirmation of already-active kits.
4. **Kit has orders** — checked only when Bitrix24 is enabled. If the kit has no linked orders, the sync is rejected with a `400` error since there is nothing to push.

---

## Execution Flow

```
1. Fetch and authorise the kit
2. Check kit.status == "AWAITING_CONFIRMATION"
3. If BITRIX_ENABLED is false → return kit as-is (no sync)
4. If kit has no orders → 400 error
5. For each order in kit.orders:
   a. Look up existing Bitrix24 product ID (mapping table)
   b. No mapping → enqueue product/create
      Mapping exists → enqueue product/update
6. Look up existing Bitrix24 deal ID (mapping table)
   a. No mapping → enqueue deal/create
      Mapping exists → enqueue deal/update
7. Update kit.status = "NEW"
8. Return updated kit
```

---

## Bitrix24 Sync Details

All sync operations are **asynchronous** — they are placed into a Redis queue (`bitrix24:queue:default`) and processed by a background worker. The HTTP response does not wait for Bitrix24 to confirm receipt.

Each entity uses an **upsert** pattern based on the local-to-external ID mapping table:

| Entity | No existing mapping | Existing mapping |
|---|---|---|
| Order | `product/create` | `product/update` |
| Kit | `deal/create` | `deal/update` |

**Order is guaranteed**: orders are always enqueued before the kit deal, so Bitrix24 receives the product line items before the deal that references them.

Failures during enqueueing are **non-fatal** — each order and the kit are wrapped in independent `try/except` blocks. A failure to enqueue one order does not prevent the others or the kit from being processed. All failures are logged at `ERROR` level with full traceback.

---

## Status Transition

| Before | After |
|---|---|
| `AWAITING_CONFIRMATION` | `NEW` |

The status is updated **after** all sync operations have been enqueued. If Bitrix24 is disabled, the status is **not** changed and the kit is returned as-is.

---

## Responses

| Status | Condition | Body |
|---|---|---|
| `200 OK` | Success | `KitOut` — the updated kit with `status: "NEW"` |
| `200 OK` | Bitrix24 disabled | `KitOut` — kit unchanged (still `AWAITING_CONFIRMATION`) |
| `400 Bad Request` | Wrong status | `{"detail": "Kit cannot be confirmed: expected status AWAITING_CONFIRMATION, got '...'"}`|
| `400 Bad Request` | Kit has no orders | `{"detail": "Kit has no orders to confirm"}` |
| `403 Forbidden` | User does not own the kit | `{"detail": "Access denied"}` |
| `404 Not Found` | Kit does not exist | `{"detail": "Kit not found"}` |
