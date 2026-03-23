# Basket API — Frontend Integration Guide

The Basket is a temporary, per-user staging area for draft manufacturing orders.  
Items live in Redis; **no Orders or Kits are created in the database** until the user explicitly checks out.  
On checkout, one `Order` per basket item is created (with full price calculation), then all of them are grouped into a single `Kit`.

---

## Table of contents

- [Authentication](#authentication)
- [Base URL](#base-url)
- [Data types](#data-types)
  - [BasketItemIn](#basketitemin-request-body)
  - [BasketItemUpdate](#basketitemupdate-request-body)
  - [BasketItemOut](#basketitemout-response)
  - [BasketOut](#basketout-response)
  - [BasketCheckoutIn](#basketchechoutin-request-body)
  - [KitOut](#kitout-response)
- [Endpoints](#endpoints)
  - [POST /basket — Add item](#post-basket--add-item)
  - [GET /basket — Get basket](#get-basket--get-basket)
  - [PATCH /basket/{item_id} — Update item](#patch-basketitem_id--update-item)
  - [DELETE /basket/{item_id} — Remove item](#delete-basketitem_id--remove-item)
  - [POST /basket/checkout — Checkout](#post-basketcheckout--checkout)
  - [DELETE /basket — Clear basket](#delete-basket--clear-basket)
- [Error reference](#error-reference)
- [Typical frontend flow](#typical-frontend-flow)

---

## Authentication

Every basket endpoint requires a valid JWT access token obtained from `POST /login`.

```http
Authorization: Bearer <access_token>
```

All requests without a valid token return **401 Unauthorized**.

---

## Base URL

```
https://<host>/
```

All paths below are relative to this base URL.

---

## Data types

### `BasketItemIn` (request body)

Used when **adding** a new item. All fields except `service_id` are optional and fall back to their defaults.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `service_id` | `string` | **yes** | — | Calculator service identifier (e.g. `"cnc_lathe"`, `"cnc_milling"`) |
| `order_name` | `string \| null` | no | `null` | Human-readable item label |
| `order_code` | `string \| null` | no | `null` | Internal article / SKU |
| `quantity` | `integer` | no | `1` | Number of parts |
| `length` | `integer \| null` | no | `null` | Part length, mm |
| `width` | `integer \| null` | no | `null` | Part width, mm |
| `height` | `integer \| null` | no | `null` | Part height, mm |
| `material_id` | `string` | no | `"alum_D16"` | Material identifier (e.g. `"steel_304"`) |
| `material_form` | `string` | no | `"rod"` | Material form (`"rod"`, `"plate"`, `"sheet"`, `"bar"`) |
| `special_instructions` | `string \| null` | no | `null` | Free-text notes for production |
| `k_otk` | `string` | no | `"1.0"` | Quality-control coefficient |
| `k_cert` | `string[]` | no | `["a","f"]` | Certification types |
| `tolerance_id` | `string` | no | `"1"` | Tolerance class identifier |
| `finish_id` | `string` | no | `"1"` | Surface finish identifier |
| `cover_id` | `string[]` | no | `["1"]` | Coating/cover identifiers |
| `document_ids` | `integer[]` | no | `[]` | IDs of pre-uploaded documents to attach |
| `location` | `string \| null` | no | `null` | Override delivery location |
| `file_id` | `integer \| null` | no | `null` | ID of an already-uploaded 3-D file (STL/STEP). When set, price is calculated from the file geometry at checkout; otherwise dimensions are used. |

---

### `BasketItemUpdate` (request body)

Used when **partially updating** an existing item (PATCH). All fields are optional; only provided fields are changed.

Same fields as `BasketItemIn` — all made `Optional`. Send only the fields you want to change.

---

### `BasketItemOut` (response)

Returned inside every basket response. Identical to `BasketItemIn` plus:

| Field | Type | Description |
|---|---|---|
| `item_id` | `string` (UUID) | Server-generated unique identifier for this basket item |

All `BasketItemIn` fields are also present with their current values.

---

### `BasketOut` (response)

Returned by all basket read/write endpoints (except checkout and clear).

```jsonc
{
  "items": [BasketItemOut, ...]
}
```

| Field | Type | Description |
|---|---|---|
| `items` | `BasketItemOut[]` | Current state of the entire basket. Empty array `[]` when basket is empty. |

---

### `BasketCheckoutIn` (request body)

Used when placing the checkout request.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `kit_name` | `string` | **yes** | — | Name for the Kit that will be created |
| `quantity` | `integer` | no | `1` | Kit quantity |
| `status` | `string \| null` | no | `"NEW"` | Initial Kit status |
| `location` | `string \| null` | no | user's location | Delivery location override |

---

### `KitOut` (response)

Returned by `POST /basket/checkout`.

| Field | Type | Description |
|---|---|---|
| `kit_id` | `integer` | Database ID of the created Kit |
| `kit_name` | `string \| null` | Name given at checkout |
| `user_id` | `integer` | Owner's user ID |
| `order_ids` | `integer[]` | IDs of the Orders created from basket items |
| `quantity` | `integer` | Kit quantity |
| `status` | `string` | Kit status (e.g. `"NEW"`) |
| `kit_price` | `number \| null` | Price per single kit unit |
| `total_kit_price` | `number \| null` | `kit_price × quantity` |
| `delivery_price` | `number \| null` | Delivery cost |
| `location` | `string \| null` | Delivery location |
| `created_at` | `string` (ISO 8601) | Creation timestamp |
| `updated_at` | `string` (ISO 8601) | Last update timestamp |

---

## Endpoints

---

### `POST /basket` — Add item

Adds a new draft order item to the authenticated user's basket. Generates a UUID `item_id` and returns the full basket.

**No database records are created.**

```http
POST /basket
Authorization: Bearer <token>
Content-Type: application/json
```

#### Request body — `BasketItemIn`

```json
{
  "service_id": "cnc_lathe",
  "order_name": "Shaft Ø40",
  "quantity": 2,
  "length": 200,
  "width": 40,
  "height": 40,
  "material_id": "steel_304",
  "material_form": "rod"
}
```

#### Response — `200 OK` — `BasketOut`

```json
{
  "items": [
    {
      "item_id": "f3a1c9d2-8b4e-4c1a-bf22-001234567890",
      "service_id": "cnc_lathe",
      "order_name": "Shaft Ø40",
      "order_code": null,
      "quantity": 2,
      "length": 200,
      "width": 40,
      "height": 40,
      "material_id": "steel_304",
      "material_form": "rod",
      "special_instructions": null,
      "k_otk": "1.0",
      "k_cert": ["a", "f"],
      "tolerance_id": "1",
      "finish_id": "1",
      "cover_id": ["1"],
      "document_ids": [],
      "location": null,
      "file_id": null
    }
  ]
}
```

#### Error responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid JWT |
| `422` | `service_id` not provided or field validation failed |

---

### `GET /basket` — Get basket

Returns the current basket contents. Returns an empty list if the basket is empty — never 404.

```http
GET /basket
Authorization: Bearer <token>
```

#### Response — `200 OK` — `BasketOut`

```json
{
  "items": [
    {
      "item_id": "f3a1c9d2-8b4e-4c1a-bf22-001234567890",
      "service_id": "cnc_lathe",
      "quantity": 2,
      ...
    },
    {
      "item_id": "9b2ee114-0011-4abc-9001-aabbccddeeff",
      "service_id": "cnc_milling",
      "quantity": 1,
      "file_id": 42,
      ...
    }
  ]
}
```

Empty basket:

```json
{ "items": [] }
```

#### Error responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid JWT |

---

### `PATCH /basket/{item_id}` — Update item

Partially updates an existing basket item. Only the fields you send are changed; all others keep their current values.

```http
PATCH /basket/{item_id}
Authorization: Bearer <token>
Content-Type: application/json
```

#### Path parameter

| Parameter | Type | Description |
|---|---|---|
| `item_id` | `string` (UUID) | The `item_id` returned when the item was added |

#### Request body — `BasketItemUpdate`

Send only the fields you want to change:

```json
{
  "quantity": 5,
  "special_instructions": "Extra polishing required"
}
```

#### Response — `200 OK` — `BasketOut`

Full updated basket (same structure as `GET /basket`).

#### Error responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid JWT |
| `404` | `item_id` not found in basket |
| `422` | Field validation failed |

---

### `DELETE /basket/{item_id}` — Remove item

Removes one item from the basket. Returns the basket without the deleted item.

```http
DELETE /basket/{item_id}
Authorization: Bearer <token>
```

#### Path parameter

| Parameter | Type | Description |
|---|---|---|
| `item_id` | `string` (UUID) | The `item_id` of the item to remove |

#### Response — `200 OK` — `BasketOut`

Full updated basket (same structure as `GET /basket`).

#### Error responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid JWT |
| `404` | `item_id` not found in basket |

---

### `POST /basket/checkout` — Checkout

Converts the basket into a Kit.

**What happens server-side:**
1. For each basket item: calculates price and creates a DB `Order` (using the uploaded file if `file_id` is set, otherwise using the stored dimensions).
2. Creates a `Kit` containing all created Orders.
3. Clears the basket on success.

> **Important:** If the basket contains many items, this request may take several seconds due to per-item calculator service calls. Show a loading state.

```http
POST /basket/checkout
Authorization: Bearer <token>
Content-Type: application/json
```

#### Request body — `BasketCheckoutIn`

```json
{
  "kit_name": "April batch – shafts",
  "quantity": 1
}
```

#### Response — `201 Created` — `KitOut`

```json
{
  "kit_id": 17,
  "kit_name": "April batch – shafts",
  "user_id": 5,
  "order_ids": [101, 102],
  "quantity": 1,
  "status": "NEW",
  "kit_price": null,
  "total_kit_price": 0.0,
  "delivery_price": null,
  "location": "Moscow",
  "created_at": "2026-03-17T14:22:00.000Z",
  "updated_at": "2026-03-17T14:22:00.000Z"
}
```

> `kit_price` and `total_kit_price` are `null` / `0.0` immediately after creation and are filled in asynchronously by the backend after order pricing completes.

#### Error responses

| Status | Condition |
|---|---|
| `400` | Basket is empty (`"Basket is empty"`) |
| `400` | One of the order payloads is invalid (e.g. invalid order data) |
| `401` | Missing or invalid JWT |
| `5xx` | Calculator service failure during order creation |

---

### `DELETE /basket` — Clear basket

Removes all items from the basket. Safe to call on an empty basket (idempotent).

```http
DELETE /basket
Authorization: Bearer <token>
```

#### Response — `204 No Content`

No response body.

#### Error responses

| Status | Condition |
|---|---|
| `401` | Missing or invalid JWT |

---

## Error reference

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|---|---|
| `400 Bad Request` | Business rule violation (e.g. empty basket checkout) |
| `401 Unauthorized` | JWT missing, expired, or invalid |
| `404 Not Found` | `item_id` does not exist in the basket |
| `422 Unprocessable Entity` | Request body failed schema validation — check `detail` for field-level errors |
| `5xx` | Server-side error (calculator service unavailable, etc.) |

---

## Typical frontend flow

```
1. User adds parts one by one
   POST /basket  ×N  →  display updated BasketOut each time

2. User adjusts a part
   PATCH /basket/{item_id}  →  display updated BasketOut

3. User removes a part
   DELETE /basket/{item_id}  →  display updated BasketOut

4. User views the basket at any time
   GET /basket  →  display BasketOut

5. User submits the basket
   POST /basket/checkout  →  KitOut (basket is now empty)
   redirect to Kit detail page using kit_id

6. User discards the basket
   DELETE /basket  →  204
```

### Notes for implementation

- **`item_id` is a UUID string.** Store it when an item is added; you'll need it for PATCH and DELETE by-item.
- **Every mutating call (POST, PATCH, DELETE by-item) returns the full updated `BasketOut`.** You do not need to call `GET /basket` after a write — just use the response directly to refresh UI state.
- **Basket TTL is 7 days of inactivity.** If the user hasn't touched their basket for 7 days, it is automatically cleared by the server; handle an empty response gracefully.
- **Checkout is not instant.** The server calls an external calculator service for each basket item sequentially. For baskets with many items, budget a few seconds per item. Disable the checkout button and show progress.
- **Basket is user-scoped.** Each authenticated user has exactly one basket. There is no concept of a guest basket.
