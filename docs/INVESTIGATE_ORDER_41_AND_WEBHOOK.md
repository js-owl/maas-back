# Investigation: Order 41 Duplicate Deals & Webhook Test

## Issue 1: Why are there 2 deals for order 41 in Bitrix?

### Investigation Steps

1. **Check Order 41 in Database**
   - Query the database to see what `bitrix_deal_id` is stored for order 41
   - Check when the order was created vs updated
   - Verify if the order was updated after creation (which could trigger duplicate deal creation)

2. **Check Bitrix for All Deals with Order 41**
   - Search Bitrix for all deals with title containing "Order #41"
   - Compare deal IDs, creation dates, and other details
   - Identify which deal is stored in the database vs duplicates

3. **Check for Root Causes**
   - **Order Update Trigger**: In `backend/orders/service.py`, the `update_order()` function checks if `bitrix_deal_id` exists. If it's `None`, it queues deal creation. This could happen if:
     - Order was created before Bitrix integration was fully set up
     - Order was updated before the deal was created and saved to DB
     - Race condition where deal creation was queued but not yet saved when update happened
   
   - **Multiple Queue Messages**: Check Redis queue for multiple deal creation messages for order 41
   
   - **Worker Processing**: Check if the worker processed the same message multiple times

### Code Locations to Check

1. **Order Creation/Update**:
   - `backend/orders/service.py`:
     - `create_order_with_calculation()` - lines 111-120 (queues deal creation)
     - `create_order_with_dimensions()` - lines 198-206 (queues deal creation)
     - `update_order()` - lines 264-278 (queues deal creation if `bitrix_deal_id` is None)

2. **Deal Creation Queue**:
   - `backend/bitrix/sync_service.py`:
     - `queue_deal_creation()` - lines 24-87 (checks if deal already exists before queuing)

3. **Worker Processing**:
   - `backend/bitrix/worker.py`:
     - `_process_deal_operation()` - lines 101-250 (checks if deal exists before creating)

### Potential Solutions

1. **Use Cleanup Service**: The codebase has a `bitrix_cleanup_service` that can find and remove duplicate deals
   - Location: `backend/bitrix/cleanup_service.py`
   - Method: `cleanup_duplicate_deals_for_order()`

2. **Fix Race Condition**: Ensure `bitrix_deal_id` is saved to database immediately after deal creation, before any updates

3. **Add Better Duplicate Prevention**: Check Bitrix directly before creating a new deal

---

## Issue 2: Did the Bitrix robot's outgoing webhook work?

### Webhook URL
```
http://192.168.0.104:8001/bitrix/webhook?test="test2"
```

### Investigation Steps

1. **Check Application Logs**
   - Look for webhook requests in `server.log` or application logs
   - Search for:
     - "Bitrix webhook received"
     - "INCOMING REQUEST" with path "/bitrix/webhook"
     - Query parameter "test" or "test2"

2. **Check Webhook Endpoint**
   - Endpoint: `POST /bitrix/webhook` (defined in `backend/bitrix/webhook_router.py`)
   - The endpoint accepts query parameters via FastAPI `Query()`
   - Query parameter `test="test2"` should be logged in the request middleware

3. **Test Webhook Manually**
   ```bash
   curl -X POST "http://192.168.0.104:8001/bitrix/webhook?test=test2" \
        -H "Content-Type: application/json" \
        -d '{}'
   ```

4. **Check Webhook Authentication**
   - The webhook requires `BITRIX_WEBHOOK_TOKEN` if configured
   - Token can be in:
     - Query parameter: `?token=...`
     - Header: `X-Bitrix-Token` or `Authorization: Bearer ...`
     - Request body: `{"token": "..."}`

5. **Check Redis Queue**
   - Webhooks are published to Redis Stream: `bitrix:webhooks`
   - Check if webhook message was queued

### Code Locations

1. **Webhook Router**: `backend/bitrix/webhook_router.py`
   - Endpoint: `bitrix_webhook()` - lines 178-293
   - Logs: Lines 239-243 log webhook receipt

2. **Request Middleware**: `backend/core/middleware.py`
   - `request_logging_middleware()` - lines 12-42
   - Logs all incoming requests with query parameters

3. **Queue Service**: `backend/bitrix/queue_service.py`
   - `publish_webhook_event()` - publishes to Redis

### How to Verify

1. **Check Logs**:
   ```bash
   # Search for webhook requests
   grep -i "webhook" server.log
   grep -i "test2" server.log
   grep -i "bitrix/webhook" server.log
   ```

2. **Check Redis**:
   - Use `check_webhook_logs.py` or similar script to check Redis stream

3. **Test Endpoint**:
   - Use `test_webhook_endpoint.py` script to test the endpoint

---

## Quick Diagnostic Commands

### Check Order 41
```python
# Run in Python with backend imports
from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.cleanup_service import bitrix_cleanup_service
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        # Get order
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        print(f"Order 41: bitrix_deal_id={order.bitrix_deal_id}")
        
        # Find all deals
        deals = await bitrix_cleanup_service.find_duplicate_deals_for_order(41, order.bitrix_deal_id)
        print(f"Found {len(deals)} deals for order 41")
        for deal in deals:
            print(f"  Deal {deal['ID']}: {deal['TITLE']}")
```

### Check Webhook Logs
```bash
# Search logs for webhook with test parameter
grep -i "test.*test2\|test2\|webhook.*test" server.log

# Search for webhook endpoint access
grep -i "bitrix/webhook" server.log | tail -20
```

---

## Next Steps

1. Run the diagnostic scripts to gather data
2. Check application logs for webhook requests
3. Query Bitrix API directly to find all deals for order 41
4. Review the order creation/update flow to identify duplicate creation point
5. Test webhook endpoint manually to verify it's accessible





