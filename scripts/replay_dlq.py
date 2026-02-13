"""Replay Bitrix24 DLQ messages back to the main queue."""
from __future__ import annotations

import argparse
import asyncio

from redis.asyncio import Redis

from backend.bitrix24.async_queue.dlq import DLQ_NAME
from backend.bitrix24.async_queue.producer import QUEUE_NAME
from backend.core.redis import create_redis_pool


async def main(count: int) -> None:
    redis = Redis(connection_pool=create_redis_pool())
    replayed = 0
    for _ in range(count):
        raw = await redis.rpop(DLQ_NAME)
        if not raw:
            break
        await redis.lpush(QUEUE_NAME, raw)
        replayed += 1
    await redis.close()
    await redis.connection_pool.disconnect(inuse_connections=True)
    print(f"Replayed {replayed} messages back to {QUEUE_NAME}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay Bitrix24 DLQ messages")
    parser.add_argument("--count", type=int, default=10, help="Max messages to replay")
    args = parser.parse_args()
    asyncio.run(main(args.count))
