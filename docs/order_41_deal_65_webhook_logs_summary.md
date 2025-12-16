# Order 41 (Deal 65) Webhook Logs Check Summary

**Date:** 2025-01-24  
**Task:** Check logs for order 41 (deal 65) changes from Bitrix (outgoing webhook)

## Executive Summary

**Key Finding:** Only **1 webhook call** found in logs, and it **failed** with "Missing entity_id" error. **No successful webhook processing** found for deal 65 or any other deal.

## Findings

### 1. Docker Container Logs - Webhook Activity
- **Total Webhook Calls Found:** 1
- **Successful Webhook Processing:** 0
- **Failed Webhook Calls:** 1

**The Only Webhook Call Found:**
```
Line 86: INCOMING REQUEST - Method: POST, Path: /bitrix/webhook, Query: test=test2
Line 87: ERROR: HTTP Exception: 400 - Missing entity_id
Line 88: REQUEST COMPLETE - Method: POST, Path: /bitrix/webhook, Status: 400, Duration: 3.08ms
Line 89: 172.21.0.1:49418 - "POST /bitrix/webhook?test=test2 HTTP/1.1" 400 Bad Request
```

**Analysis:**
- This appears to be a **test webhook call** (note the `?test=test2` query parameter)
- The webhook **failed validation** because the payload was missing `entity_id`
- This was likely a manual test, not an actual Bitrix webhook for deal 65
- **No deal 65 webhook entries found** in any logs

### 2. Redis Stream Check
- **Stream Name:** `bitrix:webhooks`
- **Total Messages Found:** 3 messages
- **Deal IDs in Stream:**
  - Deal 51: 3 webhook messages (ONCRMDEALUPDATE events)
  - **Deal 65: NOT FOUND in current stream**
  
**Recent Webhook Messages:**
```
Message ID: 1764150607469-0
- Event: ONCRMDEALUPDATE
- Entity: deal 51
- Stage: C1:NEW
- Timestamp: 2025-11-26T09:50:07.469199+00:00

Message ID: 1764152589461-0
- Event: ONCRMDEALUPDATE
- Entity: deal 51
- Stage: C1:NEW
- Timestamp: 2025-11-26T10:23:09.460581+00:00

Message ID: 1764152657687-0
- Event: ONCRMDEALUPDATE
- Entity: deal 51
- Stage: C1:NEW
- Timestamp: 2025-11-26T10:24:17.686424+00:00
```

### 3. Local Log Files
- **server.log:** Only contains server startup messages, no webhook entries
- **debug.log:** Contains HTTP connection logs, no webhook entries

## Possible Reasons for Missing Deal 65 Webhooks

1. **Already Processed and Acknowledged**
   - Webhook messages are removed from Redis stream after successful processing
   - If deal 65 webhooks were processed, they would no longer appear in the stream
   - Check worker logs or application logs for processing history

2. **Webhook Not Sent from Bitrix**
   - Bitrix may not have sent webhook for deal 65 changes
   - Check Bitrix webhook configuration
   - Verify deal 65 actually had changes that trigger webhooks

3. **Webhook Filtered Out**
   - Webhook router filters deals not in MaaS funnel (see `webhook_router.py` lines 246-267)
   - If deal 65 is not in the correct category, webhook would be acknowledged but not processed

4. **Logs Rotated/Cleared**
   - Older webhook logs may have been rotated or cleared
   - Docker logs may have been truncated

## How to Check Further

### Option 1: Check Worker Processing Logs
```bash
docker logs backend 2>&1 | findstr /i "Processing webhook\|deal 65\|_handle_deal_updated"
```

### Option 2: Check if Deal 65 Exists in Database
```python
# Check if order 41 has bitrix_deal_id = 65
# Query: SELECT order_id, bitrix_deal_id FROM orders WHERE order_id = 41;
```

### Option 3: Check Bitrix Directly
- Verify deal 65 exists in Bitrix
- Check deal 65's category and stage
- Verify webhook is configured for deal updates in Bitrix

### Option 4: Check Pending Messages
```bash
# Check for unprocessed webhook messages
docker exec redis redis-cli XPENDING bitrix:webhooks bitrix-workers
```

## Webhook Processing Flow

1. **Webhook Received** → `/bitrix/webhook` endpoint
2. **Logged** → `logger.info("Bitrix webhook received: {event_type} for {entity_type} {entity_id}")`
3. **Published to Redis** → `bitrix:webhooks` stream
4. **Worker Processes** → `BitrixWorker.process_webhook_message()`
5. **Acknowledged** → Message removed from stream after successful processing

## Additional Checks

### Consumer Group Status
- **Consumer Group:** `bitrix_workers` (not `bitrix-workers`)
- **Status:** Checked for pending messages

### API Calls Found
- Multiple `crm.deal.get` API calls found in logs
- These are direct API calls, not webhook events
- Some calls returned 400 Bad Request (deal may not exist or access denied)

## Conclusion

**No webhook activity found for deal 65 (order 41).**

The only webhook call in the logs was a **test call** that failed validation. This indicates:

1. **Bitrix has not sent any webhooks for deal 65** - No webhook events were received from Bitrix for deal 65 changes
2. **The test webhook failed** - The test call (`?test=test2`) failed because it had no `entity_id` in the payload
3. **No successful webhook processing** - No webhooks have been successfully processed in the current log history

## Next Steps

### 1. Verify Deal 65 Exists and is Configured
```sql
-- Check database
SELECT order_id, bitrix_deal_id, status, created_at, updated_at 
FROM orders 
WHERE order_id = 41;
```

### 2. Check Bitrix Webhook Configuration
- **Webhook URL:** Verify it's set to `http://192.168.0.104:8001/bitrix/webhook` (or your server IP)
- **Event Type:** Ensure `ONCRMDEALUPDATE` is enabled
- **Deal Filter:** Check if webhook filter includes deal 65's category
- **Webhook Status:** Verify webhook is active in Bitrix

### 3. Test Webhook Manually
You can test if the webhook endpoint is working by sending a proper webhook payload:
```bash
curl -X POST "http://192.168.0.104:8001/bitrix/webhook" \
     -H "Content-Type: application/json" \
     -d '{
       "event": "ONCRMDEALUPDATE",
       "data": {
         "FIELDS": {
           "ID": "65",
           "STAGE_ID": "C1:NEW",
           "CATEGORY_ID": "1"
         }
       }
     }'
```

### 4. Check if Deal 65 Had Recent Changes
- Log into Bitrix24
- Check deal 65's activity log
- Verify if any changes were made that should trigger webhooks
- Check if deal 65 is in the correct funnel/category

### 5. Monitor Webhook Endpoint
Enable more verbose logging or monitor the endpoint in real-time:
```bash
# Watch for new webhook calls
docker logs -f backend | grep -i webhook
```

## Files Created

1. **`order_41_deal_65_webhook_logs_summary.md`** - This summary document
2. **`all_webhook_activity_check.txt`** - Detailed log analysis results
3. **`check_all_webhook_activity.py`** - Script to analyze webhook activity from Docker logs

