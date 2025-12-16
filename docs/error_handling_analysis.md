# Error Handling Analysis for Bitrix Worker

## Current Behavior

When a worker task encounters a 400 error (or any error) from Bitrix:

1. **Worker returns `False`** from `process_operation_message()`
2. **Message is NOT acknowledged** (stays in pending)
3. **Retry count is checked**:
   - If `retry_count < max_retries` (5): Message stays pending, will be claimed and retried later
   - If `retry_count >= max_retries`: Message is acknowledged and removed from queue

## Problem with Current Approach

**All errors are treated the same**, including:
- **Permanent errors** (400 "Not found" - deal doesn't exist, invalid data)
- **Transient errors** (500 server error, network timeout, rate limiting)

This means:
- A 400 "Not found" error will retry 5 times (wasting resources)
- A temporary network error might be given up too early
- No distinction between recoverable and non-recoverable errors

## What Should Happen

### 1. **Permanent Errors (400 with specific messages)**
   - **"Not found"** - Deal/contact doesn't exist
     - For **update** operations: Acknowledge immediately (deal was deleted, nothing to update)
     - For **create** operations: This shouldn't happen, but if it does, log and acknowledge
   - **Invalid data/validation errors** - Data format is wrong
     - Acknowledge after 1-2 retries (won't fix itself)
     - Log error for manual investigation

### 2. **Transient Errors**
   - **500 Internal Server Error** - Bitrix server issue
     - Retry with exponential backoff (current behavior is OK)
   - **Network timeout/connection errors**
     - Retry with exponential backoff
   - **Rate limiting (429)** - Too many requests
     - Retry with longer delay

### 3. **Business Logic Errors**
   - **Deal already exists** - Duplicate creation attempt
     - Check if deal exists, update instead of create, or acknowledge
   - **Missing required fields** - Data incomplete
     - Log error, acknowledge after 1 retry (won't fix without data fix)

## Recommended Implementation

1. **Categorize errors** in `BitrixClient._post()`:
   - Return error type/category along with error response
   - Distinguish: permanent, transient, business logic

2. **Handle errors differently** in worker:
   - Permanent errors: Acknowledge after 1-2 retries
   - Transient errors: Retry with exponential backoff (current behavior)
   - Business logic: Handle case-by-case

3. **Add error details to message**:
   - Store error type/code in message metadata
   - Use for smarter retry decisions

## Current Code Flow

```
Worker processes message
  ↓
Bitrix API call (create/update)
  ↓
400 Error returned
  ↓
process_operation_message() returns False
  ↓
Worker checks retry_count
  ↓
If < 5: Message stays pending (will retry)
If >= 5: Message acknowledged (removed)
```

## Proposed Code Flow

```
Worker processes message
  ↓
Bitrix API call (create/update)
  ↓
Error returned (with error type)
  ↓
Categorize error:
  - Permanent (400 "Not found") → Acknowledge after 1 retry
  - Transient (500, timeout) → Retry with backoff
  - Business logic → Handle case-by-case
  ↓
Update retry_count and error metadata
  ↓
Acknowledge or keep pending based on error type
```









