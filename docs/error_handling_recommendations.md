# Error Handling Recommendations for Bitrix Worker

## Current Behavior (What Happens Now)

When worker encounters a **400 error** (or any error) from Bitrix:

1. **BitrixClient returns `None`** (error logged)
2. **Worker's `process_operation_message()` returns `False`**
3. **Message stays in Redis pending** (not acknowledged)
4. **Retry count checked**:
   - If `retry_count < 5`: Message will be claimed and retried later
   - If `retry_count >= 5`: Message is acknowledged and removed (gives up)

**Problem**: A 400 "Not found" error (deal doesn't exist) will retry 5 times, wasting resources.

## What SHOULD Happen

### 1. **400 "Not found" for UPDATE operations**
   - **Current**: Retries 5 times
   - **Should**: Acknowledge after 1-2 retries (deal was deleted, nothing to update)
   - **Reason**: This is a permanent error - retrying won't help

### 2. **400 "Not found" for CREATE operations**
   - **Current**: Retries 5 times
   - **Should**: Log error, acknowledge after 1 retry (shouldn't happen for create)
   - **Reason**: If create returns "not found", something is wrong with the request

### 3. **400 "Invalid data" / Validation errors**
   - **Current**: Retries 5 times
   - **Should**: Acknowledge after 1-2 retries (data format is wrong, won't fix itself)
   - **Reason**: Permanent error - needs data fix, not retry

### 4. **500 Internal Server Error**
   - **Current**: Retries 5 times
   - **Should**: Retry with exponential backoff (current behavior is OK)
   - **Reason**: Transient error - might fix itself

### 5. **429 Rate Limiting**
   - **Current**: Retries 5 times
   - **Should**: Retry with longer delay (exponential backoff)
   - **Reason**: Transient - wait and retry

### 6. **401 Authentication Error**
   - **Current**: Retries 5 times
   - **Should**: Acknowledge after 1 retry (webhook expired/invalid)
   - **Reason**: Permanent - needs config fix

## Recommended Implementation

### Option 1: Categorize Errors in BitrixClient

Modify `BitrixClient._post()` to return error information:

```python
class BitrixError:
    def __init__(self, status_code: int, error_body: str, is_permanent: bool):
        self.status_code = status_code
        self.error_body = error_body
        self.is_permanent = is_permanent

# In _post():
if status_code == 400 and "not found" in error_body.lower():
    return BitrixError(status_code, error_body, is_permanent=True)
elif status_code == 400:
    return BitrixError(status_code, error_body, is_permanent=True)  # Invalid data
elif status_code >= 500:
    return BitrixError(status_code, error_body, is_permanent=False)  # Transient
```

### Option 2: Smart Retry Logic in Worker

Modify worker to check error type and adjust retry count:

```python
# In process_operation_message():
if not success:
    retry_count = int(message.get("retry_count", "0"))
    
    # Check if error is permanent (from error metadata)
    error_type = message.get("error_type", "unknown")
    
    if error_type == "permanent":
        max_retries = 2  # Fewer retries for permanent errors
    else:
        max_retries = 5  # Full retries for transient errors
    
    if retry_count >= max_retries:
        # Acknowledge and give up
        await acknowledge_message(...)
    else:
        # Increment retry count and keep pending
        # Message will be retried later
```

### Option 3: Store Error Details in Message

When error occurs, store error type in message metadata:

```python
# When error occurs:
error_metadata = {
    "error_type": "permanent" if is_permanent else "transient",
    "error_code": status_code,
    "error_message": error_body[:100]
}
# Store in message for retry decisions
```

## Immediate Action Items

1. **For 400 "Not found" on UPDATE**: 
   - Check if deal exists before updating
   - If doesn't exist, acknowledge message immediately (nothing to update)

2. **For 400 "Not found" on CREATE**:
   - This shouldn't happen - log as error
   - Acknowledge after 1 retry

3. **For other 400 errors**:
   - Log error details
   - Acknowledge after 2 retries (won't fix itself)

4. **For 500/429 errors**:
   - Keep current retry behavior (5 retries with backoff)

## Example: Handling "Not found" for Update

```python
# In _process_deal_operation() for update:
deal_id = order.bitrix_deal_id
if not deal_id:
    logger.warning(f"Order {order_id} has no Bitrix deal ID, cannot update")
    return True  # Acknowledge - nothing to update

# Check if deal exists
deal = await bitrix_client.get_deal(deal_id)
if not deal:
    logger.warning(f"Deal {deal_id} not found in Bitrix for order {order_id}")
    # Deal was deleted - nothing to update
    return True  # Acknowledge immediately

# Proceed with update
success = await bitrix_client.update_deal(deal_id, update_fields)
```

This prevents unnecessary retries when deal doesn't exist.









