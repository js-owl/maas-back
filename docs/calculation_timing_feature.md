# Calculation Performance Tracking Feature

## Overview

The Manufacturing Service API v3.2.0 introduces comprehensive calculation performance tracking to monitor and optimize system performance. This feature provides detailed timing metrics for all calculation operations.

## Default Credentials

**Admin User:**
- Username: `admin`
- Password: `WQu^^^kLNrDDEXBJ#WJT9Z`
- Note: Password already changed in development

**Test User:**
- Username: `testuser`
- Password: `testpass123`

## Features

- **Dual Timing Metrics**: Track both calculator service call time and total backend processing time
- **Automatic Tracking**: All calculations automatically include timing data
- **Order Recalculation**: New endpoint to recalculate existing orders with updated timing
- **Performance Monitoring**: Use timing data to monitor system performance and optimize bottlenecks

## Timing Fields

### calculation_time
- **Type:** `float`
- **Description:** Calculator service call duration only (port 7000)
- **Unit:** seconds
- **When Tracked:** All calculation operations
- **Example:** `0.856`

### total_calculation_time
- **Type:** `float`
- **Description:** Total backend processing time including:
  - File retrieval from database
  - Base64 encoding/decoding
  - Calculator service call
  - Response mapping and processing
- **Unit:** seconds
- **When Tracked:** All calculation operations
- **Example:** `0.862`

## When Timing is Tracked

### 1. Price Calculation
**Endpoint:** `POST /calculate-price`

All price calculations include both timing fields in the response.

**Example Response:**
```json
{
  "service_id": "cnc-milling",
  "detail_price": 2133.23,
  "calculation_type": "ml_based",
  "calculation_time": 0.856,
  "total_calculation_time": 0.862
}
```

### 2. Order Creation
**Endpoint:** `POST /orders`

When creating orders, timing data is stored in the database and returned in the response.

**Example Response:**
```json
{
  "order_id": 123,
  "detail_price": 2133.23,
  "calculation_type": "ml_based",
  "calculation_time": 0.856,
  "total_calculation_time": 0.862,
  "created_at": "2025-10-16T12:00:00Z"
}
```

### 3. Order Recalculation
**Endpoint:** `POST /orders/{order_id}/recalculate`

Recalculating orders updates the timing data with new measurements.

**Example Response:**
```json
{
  "order_id": 123,
  "detail_price": 2133.23,
  "calculation_time": 0.856,
  "total_calculation_time": 0.862,
  "updated_at": "2025-10-16T12:05:00Z"
}
```

### 4. Bulk Recalculation
**Endpoint:** `POST /admin/orders/recalc-sync`

Bulk recalculation operations update timing for all processed orders.

## Performance Monitoring

### Database Queries

Monitor average performance:
```sql
-- Average calculation times
SELECT 
  AVG(calculation_time) as avg_calc_time,
  AVG(total_calculation_time) as avg_total_time,
  AVG(total_calculation_time - calculation_time) as avg_overhead
FROM orders 
WHERE created_at > '2025-10-01';
```

Monitor performance by calculation type:
```sql
-- Performance by calculation type
SELECT 
  calculation_type,
  COUNT(*) as count,
  AVG(calculation_time) as avg_calc_time,
  AVG(total_calculation_time) as avg_total_time
FROM orders 
WHERE calculation_time IS NOT NULL
GROUP BY calculation_type;
```

### Performance Thresholds

**Good Performance:**
- `calculation_time` < 1.0 seconds
- `total_calculation_time` < 1.5 seconds
- Overhead < 0.5 seconds

**Warning Performance:**
- `calculation_time` 1.0-2.0 seconds
- `total_calculation_time` 1.5-3.0 seconds
- Overhead 0.5-1.0 seconds

**Poor Performance:**
- `calculation_time` > 2.0 seconds
- `total_calculation_time` > 3.0 seconds
- Overhead > 1.0 seconds

## Troubleshooting

### High calculation_time
- Check calculator service (port 7000) performance
- Verify network connectivity
- Monitor calculator service logs

### High total_calculation_time with low calculation_time
- Check file retrieval performance
- Verify database query performance
- Monitor base64 encoding/decoding

### Missing timing data
- Ensure API version 3.2.0+
- Check for calculation errors
- Verify timing implementation

## API Integration

### Frontend Integration

Include timing fields in your frontend monitoring:

```javascript
// Example: Track calculation performance
const response = await fetch('/calculate-price', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(calcData)
});

const data = await response.json();

// Log performance metrics
console.log(`Calculation: ${data.calculation_time}s`);
console.log(`Total: ${data.total_calculation_time}s`);
console.log(`Overhead: ${data.total_calculation_time - data.calculation_time}s`);
```

### Monitoring Dashboard

Create performance dashboards using timing data:

```sql
-- Performance trends over time
SELECT 
  DATE(created_at) as date,
  AVG(calculation_time) as avg_calc_time,
  AVG(total_calculation_time) as avg_total_time
FROM orders 
WHERE created_at > '2025-10-01'
GROUP BY DATE(created_at)
ORDER BY date;
```

## Migration Notes

### From v3.1.0 to v3.2.0

- New timing fields are automatically added to all responses
- Existing orders will have `NULL` timing values until recalculated
- Use `/orders/{order_id}/recalculate` to populate timing for existing orders

### Database Schema

New columns added to `orders` table:
- `calculation_time` (REAL, nullable)
- `total_calculation_time` (REAL, nullable)

## Best Practices

1. **Monitor Regularly**: Set up alerts for performance thresholds
2. **Track Trends**: Monitor performance over time to identify degradation
3. **Optimize Bottlenecks**: Use timing data to identify and fix performance issues
4. **Document Issues**: Log performance anomalies for investigation
5. **Test Performance**: Include timing validation in your test suite
