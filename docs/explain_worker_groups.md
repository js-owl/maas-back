# Worker vs Workers Consumer Groups - Explanation

## The Issue

There are **TWO** consumer groups in Redis:

1. **`bitrix_worker`** (singular) - Created accidentally by test scripts
   - 1 consumer: `worker_1`
   - 5 pending messages
   - This is NOT used by the actual worker code

2. **`bitrix_workers`** (plural) - The actual one used by the code
   - 47 consumers (many stale from previous restarts)
   - 5 pending messages
   - This is what the worker code uses (see `backend/bitrix/queue_service.py` line 25)

## Why Two Groups?

- The code uses `bitrix_workers` (plural) - see `queue_service.py`:
  ```python
  self.consumer_group = "bitrix_workers"
  ```

- My test script `check_redis_worker_status.py` accidentally created `bitrix_worker` (singular) when it tried to read messages

## The Real Problem

The worker is using `bitrix_workers` (plural), but:
- It's not running (`worker.running = False`)
- There are 47 stale consumers from previous restarts
- Messages are piling up and not being processed

## Solution

1. The worker should be using `bitrix_workers` (which it is)
2. We need to ensure the worker actually starts and stays running
3. We could clean up stale consumers, but that's not critical - they'll just accumulate

## Consumer Group Purpose

Consumer groups in Redis Streams allow:
- Multiple workers to process messages from the same stream
- Each message is delivered to only ONE consumer in the group
- Messages can be acknowledged when processed
- Pending messages can be claimed by other consumers if one dies

The plural name `bitrix_workers` suggests it's designed for multiple worker instances, which is correct.









