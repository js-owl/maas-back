# API Reference v3.2.0

## Overview

This document provides comprehensive API reference for the Manufacturing Service API v3.2.0, including all endpoints, request/response schemas, and complete examples.

## Authentication

All API endpoints require authentication using JWT Bearer tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Default Credentials

**Admin User:**
- Username: `admin`
- Password: `WQu^^^kLNrDDEXBJ#WJT9Z`
- Note: Password already changed in development

**Test User:**
- Username: `testuser`
- Password: `testpass123`

## Base URL

```
http://localhost:8000
```

## Response Examples

### Calculate Price Response

**Endpoint:** `POST /calculate-price`

**Complete Response Example:**
```json
{
  "service_id": "cnc-milling",
  "quantity": 1,
  "length": null,
  "width": null,
  "n_dimensions": 1,
  "k_otk": "1",
  "mat_volume": null,
  "detail_price": 2133.23,
  "detail_price_one": 2133.23,
  "mat_weight": null,
  "mat_price": 5.0,
  "work_price": 2031.65,
  "k_quantity": 1.0,
  "detail_time": 2.32,
  "total_price": 2138.23,
  "total_time": 2.32,
  "manufacturing_cycle": 10.0,
  "suitable_machines": ["machine_101", "machine_102", "SGT-MC116"],
  "calculation_type": "ml_based",
  "ml_model": "cnc_milling_xgboost_v2",
  "ml_confidence": 0.95,
  "calculation_engine": "ml_model",
  "calculation_time": 0.856,
  "total_calculation_time": 0.862
}
```

**Field Descriptions:**
- `calculation_time`: Calculator service call duration in seconds
- `total_calculation_time`: Total backend processing time in seconds (file retrieval + base64 conversion + service call + response mapping)
- `calculation_type`: "ml_based", "rule_based", or "unknown"
- `ml_model`: ML model name if available
- `ml_confidence`: ML confidence score (0.0-1.0) if available
- `calculation_engine`: Original calculation engine from calculator service

### Order Response

**Endpoint:** `GET /orders/{order_id}`

**Complete Response Example:**
```json
{
  "order_id": 123,
  "user_id": 1,
  "service_id": "cnc-milling",
  "file_id": 1,
  "quantity": 1,
  "length": null,
  "width": null,
  "height": null,
  "n_dimensions": 1,
  "material_id": "alum_D16",
  "material_form": "rod",
  "tolerance_id": "1",
  "finish_id": "1",
  "cover_id": ["1"],
  "k_otk": "1",
  "k_cert": ["a", "f"],
  "detail_price": 2133.23,
  "total_price": 2138.23,
  "status": "pending",
  "calculation_type": "ml_based",
  "ml_model": "cnc_milling_xgboost_v2",
  "ml_confidence": 0.95,
  "calculation_time": 0.856,
  "total_calculation_time": 0.862,
  "created_at": "2025-10-16T12:00:00Z",
  "updated_at": "2025-10-16T12:00:00Z",
  "bitrix_deal_id": null,
  "invoice_url": null,
  "invoice_file_path": null,
  "invoice_generated_at": null,
  "document_ids": null,
  "message": null
}
```

## New Endpoints in v3.2.0

### Order Recalculation

**Endpoint:** `POST /orders/{order_id}/recalculate`

**Description:** Recalculate order price using current parameters and update timing data.

**Request:**
- Path parameter: `order_id` (integer)
- Headers: `Authorization: Bearer <token>`

**Response:** Complete order object with updated calculation and timing data.

**Example Response:**
```json
{
  "order_id": 123,
  "user_id": 1,
  "service_id": "cnc-milling",
  "file_id": 1,
  "quantity": 1,
  "detail_price": 2133.23,
  "total_price": 2138.23,
  "calculation_type": "ml_based",
  "ml_model": "cnc_milling_xgboost_v2",
  "ml_confidence": 0.95,
  "calculation_time": 0.856,
  "total_calculation_time": 0.862,
  "updated_at": "2025-10-16T12:05:00Z"
}
```

## Timing Fields

### calculation_time
- **Type:** float
- **Description:** Duration of calculator service call only (port 7000)
- **Unit:** seconds
- **Example:** 0.856

### total_calculation_time
- **Type:** float
- **Description:** Total backend processing time including file retrieval, base64 conversion, service call, and response mapping
- **Unit:** seconds
- **Example:** 0.862

## Demo Files

The following demo files are available for testing (ID 1-5):

- **ID 1:** `demo_printing_default.stl` - Default model for 3D printing
- **ID 2:** `demo_lathe_default.stl` - Default model for lathe operations
- **ID 3:** `demo_3.stl` - Additional demo model
- **ID 4:** `demo_milling_default.stl` - Default model for CNC milling
- **ID 5:** `demo_5.stp` - Additional demo model (STEP format)

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

### 404 Not Found
```json
{
  "detail": "Order not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "service_id"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Performance Monitoring

Use the timing fields to monitor API performance:

- **calculation_time**: Monitor calculator service performance
- **total_calculation_time**: Monitor overall backend performance
- **Difference**: Indicates overhead (file processing, network, etc.)

Example monitoring query:
```sql
SELECT 
  AVG(calculation_time) as avg_calc_time,
  AVG(total_calculation_time) as avg_total_time,
  AVG(total_calculation_time - calculation_time) as avg_overhead
FROM orders 
WHERE created_at > '2025-10-01';
```
