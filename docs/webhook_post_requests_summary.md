# Webhook POST Requests Check Summary

**Date:** 2025-01-24  
**Search Pattern:** `POST http://192.168.137.1:8001/bitrix/webhook?test="test2"&entity_id={{ID элемента CRM}}`

## Search Results

### Requests Found

**Total webhook POST requests:** 3 (all related to the same single call)

**The only webhook POST request found:**
```
Line 87: INCOMING REQUEST - Method: POST, Path: /bitrix/webhook, Query: test=test2
Line 89: REQUEST COMPLETE - Method: POST, Path: /bitrix/webhook, Status: 400
Line 90: 172.21.0.1:49418 - "POST /bitrix/webhook?test=test2 HTTP/1.1" 400 Bad Request
```

### Key Findings

1. **No `entity_id` parameter found:**
   - The request only has `test=test2` parameter
   - No `entity_id` parameter in query string
   - This is why it failed with "Missing entity_id" error

2. **IP Address mismatch:**
   - **Expected IP:** `192.168.137.1` (from your search pattern)
   - **Actual IP:** `172.21.0.1` (Docker internal network)
   - **Note:** The request came from Docker's internal network, not from external IP 192.168.137.1

3. **No requests matching the full pattern:**
   - No requests found with both `test="test2"` AND `entity_id` parameters
   - No requests from IP `192.168.137.1`
   - No requests with `entity_id=65` or `entity_id=41`

## Analysis

The search pattern you provided suggests Bitrix should be sending webhooks with:
- `test="test2"` parameter
- `entity_id={{ID элемента CRM}}` parameter (where `{{ID элемента CRM}}` would be replaced with the actual entity ID, like 65)

**However, no such requests were found in the logs.**

## Possible Explanations

1. **Bitrix hasn't sent webhooks with this format yet**
   - The webhook configuration in Bitrix might not be set up to include `entity_id` in query parameters
   - Bitrix might be sending webhooks in the request body instead of query parameters

2. **Webhook URL mismatch**
   - Bitrix might be configured to send to a different URL
   - The IP `192.168.137.1` might not be the correct server IP
   - Check Bitrix webhook configuration for the actual URL being used

3. **Requests filtered or not logged**
   - Requests might be coming from a different IP (like `192.168.137.1`) but being proxied/forwarded
   - The middleware might not be logging query parameters correctly
   - Requests might be failing before reaching the application

4. **Different webhook format**
   - Bitrix might be sending `entity_id` in the request body, not query parameters
   - The webhook payload format might be different from expected

## Recommendations

1. **Check Bitrix Webhook Configuration:**
   - Verify the webhook URL is set to: `http://192.168.137.1:8001/bitrix/webhook`
   - Check if `entity_id` is configured to be in query parameters or request body
   - Verify the webhook is active and enabled

2. **Monitor in real-time:**
   ```bash
   # Watch for incoming webhook requests
   docker logs -f backend | grep -i "bitrix/webhook"
   ```

3. **Check network/firewall:**
   - Verify if requests from `192.168.137.1` are reaching the server
   - Check if there's a proxy/load balancer in between
   - Verify Docker port mapping (8001:8000)

4. **Test the endpoint manually:**
   ```bash
   curl -X POST "http://192.168.137.1:8001/bitrix/webhook?test=test2&entity_id=65" \
        -H "Content-Type: application/json" \
        -d '{"event": "ONCRMDEALUPDATE", "data": {"FIELDS": {"ID": "65"}}}'
   ```

5. **Check if entity_id is in request body:**
   - The webhook router expects `entity_id` in the request body (JSON payload)
   - Bitrix might be sending it in the body, not query parameters
   - Check the webhook payload format in Bitrix configuration

## Current Webhook Request Format

Based on the code in `backend/bitrix/webhook_router.py`, the webhook endpoint expects:
- **Request body:** JSON with event data (e.g., `{"event": "ONCRMDEALUPDATE", "data": {"FIELDS": {"ID": "65", ...}}}`)
- **Query parameters:** Optional (like `token` for authentication)

The `entity_id` is extracted from the JSON payload, not from query parameters.

## Conclusion

**No POST requests found matching the pattern `test="test2"&entity_id={{ID}}`.**

The only webhook request found had `test=test2` but no `entity_id` parameter, and it came from a different IP (Docker internal network) than expected.


