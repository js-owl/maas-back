# Bitrix Webhook Test Endpoint

A simple test endpoint has been added to capture and log all incoming webhook requests from Bitrix.

## Endpoint

**URL:** `POST http://your-server:8001/bitrix/webhook/test`

**Authentication:** None required (completely open for testing)

## What It Does

This endpoint:
- ✅ Accepts ANY POST request (no authentication)
- ✅ Logs ALL request details:
  - Headers
  - Query parameters
  - Raw request body
  - Parsed JSON body (if applicable)
  - URL details
  - Client IP address
- ✅ Returns a JSON response with request summary
- ✅ Prints details to both logs and console for immediate visibility

## Usage

### 1. Configure Bitrix Webhook

In Bitrix24, set your webhook URL to:
```
http://192.168.137.1:8001/bitrix/webhook/test
```
(Replace with your actual server IP)

### 2. Monitor Logs

Watch the logs in real-time:
```bash
docker logs -f backend | grep -A 50 "BITRIX WEBHOOK TEST"
```

Or check all logs:
```bash
docker logs backend | grep -A 50 "BITRIX WEBHOOK TEST"
```

### 3. Test Manually

You can also test manually with curl:

```bash
# Test with query parameters
curl -X POST "http://192.168.137.1:8001/bitrix/webhook/test?test=test2&entity_id=65" \
     -H "Content-Type: application/json" \
     -d '{"event": "ONCRMDEALUPDATE", "data": {"FIELDS": {"ID": "65"}}}'

# Test with just query parameters
curl -X POST "http://192.168.137.1:8001/bitrix/webhook/test?test=test2&entity_id=65"

# Test with empty body
curl -X POST "http://192.168.137.1:8001/bitrix/webhook/test?test=test2&entity_id=65" \
     -H "Content-Type: application/json" \
     -d '{}'
```

## Response Format

The endpoint returns a JSON response:

```json
{
  "status": "received",
  "message": "Webhook test endpoint received request - check logs for full details",
  "summary": {
    "method": "POST",
    "path": "/bitrix/webhook/test",
    "client_ip": "192.168.137.1",
    "query_params": {
      "test": "test2",
      "entity_id": "65"
    },
    "body_length": 123,
    "body_is_json": true,
    "headers_count": 15
  },
  "query_params": {
    "test": "test2",
    "entity_id": "65"
  },
  "body_preview": "...",
  "body_json": {...}
}
```

## What to Look For

When Bitrix sends a webhook, check the logs for:

1. **Query Parameters:**
   - Does it include `entity_id`?
   - Does it include `test` parameter?
   - What other parameters are sent?

2. **Request Body:**
   - What format is the JSON?
   - Where is the entity ID located?
   - What fields are included?

3. **Headers:**
   - What headers does Bitrix send?
   - Is there authentication in headers?

4. **Client IP:**
   - What IP is Bitrix sending from?
   - Is it the expected IP?

## Example Log Output

```
================================================================================
BITRIX WEBHOOK TEST ENDPOINT - FULL REQUEST DETAILS
================================================================================
Method: POST
URL: http://192.168.137.1:8001/bitrix/webhook/test?test=test2&entity_id=65
Path: /bitrix/webhook/test
Client IP: 192.168.137.1
Query Parameters: {
  "test": "test2",
  "entity_id": "65"
}
Headers: {
  "host": "192.168.137.1:8001",
  "content-type": "application/json",
  "user-agent": "Bitrix24/1.0",
  ...
}
Raw Body (length: 234 bytes):
{"event": "ONCRMDEALUPDATE", "data": {"FIELDS": {"ID": "65", "STAGE_ID": "C1:NEW"}}}
Parsed JSON Body:
{
  "event": "ONCRMDEALUPDATE",
  "data": {
    "FIELDS": {
      "ID": "65",
      "STAGE_ID": "C1:NEW"
    }
  }
}
================================================================================
```

## Next Steps

Once you see the actual format Bitrix is sending:

1. **Update the main webhook endpoint** (`/bitrix/webhook`) to handle that format
2. **Extract entity_id** from the correct location (query params, body, headers)
3. **Update the parser** in `parse_bitrix_webhook()` if needed

## Security Note

⚠️ **This endpoint has NO authentication** - it's for testing only!

Once you understand the format, you can:
- Remove this test endpoint, or
- Add authentication to it, or
- Keep it for debugging but restrict access

## Files Modified

- `backend/bitrix/webhook_router.py` - Added test endpoint


