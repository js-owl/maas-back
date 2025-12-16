# How to Check Redis for ONCRMDEALUPDATE Messages

## Quick Check Commands

### Option 1: Using the existing script
```bash
docker exec backend python3 /app/check_webhook_redis.py
```

### Option 2: Direct Redis CLI
```bash
# Check stream length
docker exec redis redis-cli XLEN bitrix:webhooks

# View recent messages
docker exec redis redis-cli XRANGE bitrix:webhooks - + COUNT 20

# Search for ONCRMDEALUPDATE
docker exec redis redis-cli XRANGE bitrix:webhooks - + COUNT 100 | grep -i "ONCRMDEALUPDATE\|deal_updated"
```

### Option 3: Using Python script (run locally)
```bash
python check_redis_webhooks_simple.py
# Results will be in redis_webhooks_check.txt
```

## What to Look For

### ONCRMDEALUPDATE Messages
- **Event Type**: Should contain "ONCRMDEALUPDATE" or "deal_updated"
- **Entity Type**: Should be "deal"
- **Entity ID**: The deal ID from Bitrix
- **Data**: Contains deal information including:
  - `ID`: Deal ID
  - `STAGE_ID`: Current stage
  - `OLD_STAGE_ID`: Previous stage (if changed)
  - `CATEGORY_ID`: Funnel category ID
  - `TITLE`: Deal title
  - `OPPORTUNITY`: Deal amount

### Stream Information
- **Stream Name**: `bitrix:webhooks`
- **Message Format**: 
  - `event_type`: Event type (e.g., "ONCRMDEALUPDATE", "deal_updated")
  - `entity_type`: "deal", "contact", or "lead"
  - `entity_id`: Entity ID
  - `data`: JSON string with entity data
  - `timestamp`: ISO timestamp

## Expected Results

If webhooks are working:
- Stream should have messages
- Messages should have `event_type` containing "ONCRMDEALUPDATE" or "deal_updated"
- `entity_type` should be "deal"
- `data` field should contain deal information

If no messages:
- Webhooks may not be configured in Bitrix
- Webhook endpoint may not be receiving requests
- Check webhook endpoint logs: `docker logs backend | grep webhook`

## Troubleshooting

### No messages in stream
1. Check if webhook endpoint is receiving requests:
   ```bash
   docker logs backend | grep -i "webhook\|bitrix/webhook"
   ```

2. Verify webhook is configured in Bitrix24
3. Check if webhook URL is correct: `http://192.168.0.104:8001/bitrix/webhook`

### Messages present but not ONCRMDEALUPDATE
- Check `event_type` field in messages
- Verify Bitrix webhook is configured for `ONCRMDEALUPDATE` event
- Check if webhook filter is set correctly in Bitrix

### Messages not being processed
- Check consumer group status
- Check worker logs: `docker logs backend | grep -i worker`
- Verify worker is running and consuming messages

## Scripts Created

1. **check_oncrmdealuPDATE_messages.py** - Comprehensive check for ONCRMDEALUPDATE messages
2. **check_redis_webhooks_simple.py** - Simple check with file output
3. **check_webhook_redis.py** - Basic webhook stream check (already exists)

## Next Steps

1. Run one of the check commands above
2. Review the output to see if ONCRMDEALUPDATE messages are present
3. If messages are present, check if they're being processed by the worker
4. If no messages, verify webhook configuration in Bitrix24





