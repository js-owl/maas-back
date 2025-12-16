# Bitrix Redis Worker Diagnostics Guide

This guide explains how to diagnose issues with the Bitrix Redis worker integration, which automatically syncs orders and users to Bitrix CRM.

## Overview

The Bitrix integration uses Redis Streams to queue operations (deal creation/updates, contact creation/updates) and a background worker to process them. The workflow is:

1. **Queue Operations**: When orders/users are created/updated, operations are queued to Redis Streams
2. **Worker Processing**: Background worker consumes messages from Redis Streams
3. **Bitrix API Calls**: Worker calls Bitrix API to create/update deals and contacts
4. **Acknowledge**: Messages are acknowledged after successful processing

## Diagnostic Endpoints

### 1. Worker Status

**Endpoint**: `GET /bitrix/sync/worker/status` (Admin only)

**Purpose**: Check if the worker is running and configured correctly.

**Response Example**:
```json
{
  "success": true,
  "message": "Worker status retrieved",
  "data": {
    "worker_enabled": true,
    "worker_running": true,
    "worker_task_exists": true,
    "worker_task_status": "running",
    "pending_messages_count": 5,
    "worker_config": {
      "max_retries": 5,
      "batch_size": 10,
      "poll_interval": 1.0
    }
  }
}
```

**What to Check**:
- `worker_enabled`: Should be `true` if `BITRIX_WORKER_ENABLED=true` in environment
- `worker_running`: Should be `true` if worker loop is active
- `worker_task_exists`: Should be `true` if worker task was created on startup
- `worker_task_status`: Should be `"running"`, not `"done"`
- `pending_messages_count`: Number of unprocessed messages (should decrease over time)

### 2. Queue Status

**Endpoint**: `GET /bitrix/sync/status` (Admin only)

**Purpose**: Check Redis Stream status and message counts.

**Response Example**:
```json
{
  "success": true,
  "message": "Sync status retrieved",
  "data": {
    "operations_stream": {
      "length": 10,
      "groups": 1,
      "last_id": "1234567890-0"
    },
    "webhooks_stream": {
      "length": 2,
      "groups": 1,
      "last_id": "1234567891-0"
    },
    "total_messages": 12,
    "bitrix_configured": true
  }
}
```

**What to Check**:
- `operations_stream.length`: Number of messages in operations stream (should be low if worker is processing)
- `webhooks_stream.length`: Number of webhook messages
- `bitrix_configured`: Should be `true` if Bitrix is properly configured

## Log Analysis

### Log Prefixes

The system uses prefixes to identify different stages of processing:

- `[QUEUE]`: Messages being published to Redis Streams
- `[WORKER]`: Messages being processed by the worker
- `[QUEUE_DEAL]`: Deal creation/update operations
- `[QUEUE_DEAL_UPDATE]`: Deal update operations
- `[QUEUE_CONTACT]`: Contact creation operations
- `[QUEUE_CONTACT_UPDATE]`: Contact update operations

### Key Log Messages

#### Worker Startup
```
INFO: Starting Bitrix worker background task...
INFO: Starting Bitrix worker - entering process_messages()
INFO: Worker loop iteration 1 - running=True
```

**If missing**: Worker may not be starting. Check:
- `BITRIX_WORKER_ENABLED` environment variable
- Application startup logs for errors
- Container/process status

#### Message Publishing
```
INFO: [QUEUE] Published create operation for deal 123 to stream bitrix:operations (message_id: 1234567890-0)
INFO: [QUEUE_DEAL] Queued deal creation for order 123 (message_id: 1234567890-0)
```

**If missing**: Operations may not be queued. Check:
- Trigger points in code (order/user creation/update)
- Redis connection
- Error logs for queue failures

#### Message Processing
```
INFO: [WORKER] Processing create operation for deal 123 (retry: 0, message_id: 1234567890-0)
INFO: Created Bitrix deal 456 for order 123
```

**If missing**: Worker may not be reading messages. Check:
- Worker running status
- Consumer group configuration
- Redis connection from worker

#### Success
```
INFO: [WORKER] Processing create operation for deal 123 (retry: 0, message_id: 1234567890-0)
INFO: Created Bitrix deal 456 for order 123
INFO: Updated order 123 with Bitrix deal ID 456
```

#### Errors
```
ERROR: [WORKER] Error processing operation message: ...
ERROR: Failed to create Bitrix deal for order 123
WARNING: Message 1234567890-0 will be retried (retry 1/5)
```

## Common Issues and Solutions

### Issue 1: Worker Not Running

**Symptoms**:
- `worker_running: false` in status endpoint
- No `[WORKER]` log messages
- Messages accumulating in Redis stream

**Diagnosis**:
```bash
# Check worker status endpoint
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/bitrix/sync/worker/status

# Check application logs for worker startup
docker logs <backend_container> | grep -i "worker"
```

**Solutions**:
1. Check `BITRIX_WORKER_ENABLED` environment variable is set to `true`
2. Check application startup logs for worker initialization errors
3. Restart the application/container
4. Check if worker task was created: look for "Bitrix worker task created" in logs

### Issue 2: Messages Not Being Published

**Symptoms**:
- No `[QUEUE]` log messages when orders/users are created/updated
- `operations_stream.length` not increasing
- Operations not appearing in Bitrix

**Diagnosis**:
```bash
# Check if queue operations are being called
docker logs <backend_container> | grep -i "\[QUEUE"

# Check Redis stream directly
docker exec -it <redis_container> redis-cli
> XINFO STREAM bitrix:operations
```

**Solutions**:
1. Verify trigger points are calling queue operations:
   - Order creation: `queue_deal_creation`
   - Order update: `queue_deal_update`
   - User creation: `queue_contact_creation`
   - User update: `queue_contact_update`
2. Check Redis connection: verify `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
3. Check for exceptions in logs when queue operations are called

### Issue 3: Messages Not Being Processed

**Symptoms**:
- `pending_messages_count` increasing
- `operations_stream.length` not decreasing
- Worker running but not processing messages

**Diagnosis**:
```bash
# Check worker is reading messages
docker logs <backend_container> | grep -i "\[WORKER\]"

# Check consumer group status
docker exec -it <redis_container> redis-cli
> XINFO GROUPS bitrix:operations
> XPENDING bitrix:operations bitrix_workers
```

**Solutions**:
1. Check consumer group exists: `XINFO GROUPS bitrix:operations`
2. Check for pending messages: `XPENDING bitrix:operations bitrix_workers`
3. Verify worker can connect to Redis
4. Check for processing errors in logs
5. Restart worker (restart application)

### Issue 4: Processing Failures

**Symptoms**:
- Messages being retried repeatedly
- Error logs showing Bitrix API failures
- Messages eventually acknowledged after max retries

**Diagnosis**:
```bash
# Check error logs
docker logs <backend_container> | grep -i "error.*bitrix"

# Check retry counts
docker logs <backend_container> | grep -i "retry"
```

**Common Causes**:
1. **Bitrix API Errors**:
   - Invalid webhook URL or expired token
   - Missing required fields
   - Rate limiting
   - Network issues

2. **Data Issues**:
   - Missing user/order data
   - Invalid field values
   - Duplicate creation attempts

**Solutions**:
1. Check Bitrix webhook URL is valid and not expired
2. Verify required fields are present in payload
3. Check Bitrix API error messages in logs
4. Review data validation in worker processing logic

### Issue 5: Consumer Group Issues

**Symptoms**:
- `NOGROUP` errors in logs
- Messages not being read
- Consumer group missing

**Diagnosis**:
```bash
# Check consumer groups
docker exec -it <redis_container> redis-cli
> XINFO GROUPS bitrix:operations
```

**Solutions**:
1. Consumer group is created automatically on first read
2. If missing, restart worker (it will recreate the group)
3. Check for `NOGROUP` errors in logs and ensure they're handled

## Manual Testing

### Test Order Creation

1. Create an order via API:
```bash
curl -X POST http://localhost:8000/orders \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"service_id": "cnc-milling", ...}'
```

2. Check logs for queue operation:
```bash
docker logs <backend_container> | grep -i "\[QUEUE_DEAL\]"
```

3. Check worker processes message:
```bash
docker logs <backend_container> | grep -i "\[WORKER\].*deal"
```

4. Verify deal created in Bitrix (check Bitrix CRM)

### Test Order Update

1. Update an order:
```bash
curl -X PUT http://localhost:8000/orders/123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}'
```

2. Check for deal update queue:
```bash
docker logs <backend_container> | grep -i "\[QUEUE_DEAL_UPDATE\]"
```

3. Verify deal updated in Bitrix

### Test User Update

1. Update user profile:
```bash
curl -X PUT http://localhost:8000/profile \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "newemail@example.com"}'
```

2. Check for contact update queue:
```bash
docker logs <backend_container> | grep -i "\[QUEUE_CONTACT_UPDATE\]"
```

3. Verify contact updated in Bitrix

## Redis Stream Commands

### Check Stream Length
```bash
docker exec -it <redis_container> redis-cli
> XLEN bitrix:operations
```

### Read Recent Messages
```bash
docker exec -it <redis_container> redis-cli
> XREVRANGE bitrix:operations + - COUNT 10
```

### Check Consumer Groups
```bash
docker exec -it <redis_container> redis-cli
> XINFO GROUPS bitrix:operations
```

### Check Pending Messages
```bash
docker exec -it <redis_container> redis-cli
> XPENDING bitrix:operations bitrix_workers
```

### Claim Pending Messages (Manual Retry)
```bash
docker exec -it <redis_container> redis-cli
> XCLAIM bitrix:operations bitrix_workers worker_<id> 60000 <message_id>
```

## Environment Variables

Ensure these are set correctly:

- `BITRIX_WORKER_ENABLED=true` - Enable worker
- `BITRIX_ENABLED=true` - Enable Bitrix integration
- `BITRIX_WEBHOOK_URL=<url>` - Bitrix webhook URL
- `REDIS_HOST=<host>` - Redis host
- `REDIS_PORT=6379` - Redis port
- `REDIS_PASSWORD=<password>` - Redis password (if required)
- `REDIS_STREAM_PREFIX=bitrix:` - Stream prefix

## Monitoring Checklist

Regular monitoring should check:

- [ ] Worker is running (`worker_running: true`)
- [ ] Pending messages count is low (< 10)
- [ ] No error messages in logs
- [ ] Messages are being processed (log timestamps are recent)
- [ ] Bitrix deals/contacts are being created/updated
- [ ] No `NOGROUP` or connection errors

## Troubleshooting Workflow

1. **Check Worker Status**: Use `/bitrix/sync/worker/status` endpoint
2. **Check Queue Status**: Use `/bitrix/sync/status` endpoint
3. **Review Logs**: Look for `[QUEUE]` and `[WORKER]` messages
4. **Check Redis**: Verify stream length and consumer groups
5. **Test Manually**: Create/update order/user and trace through logs
6. **Verify Bitrix**: Check if operations actually happened in Bitrix CRM

## Additional Resources

- Bitrix API Documentation: Check Bitrix REST API docs for field requirements
- Redis Streams Documentation: Understanding Redis Streams and consumer groups
- Application Logs: Primary source of diagnostic information









