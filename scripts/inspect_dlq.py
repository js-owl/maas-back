"""Inspect Bitrix24 DLQ messages."""
from __future__ import annotations

import argparse
import asyncio

from redis.asyncio import Redis

from backend.bitrix24.async_queue.dlq import DLQ_NAME
from backend.bitrix24.async_queue.message import deserialize_message
from backend.core.redis import create_redis_pool


async def main(limit: int) -> None:
    redis = Redis(connection_pool=create_redis_pool())
    messages = await redis.lrange(DLQ_NAME, 0, limit - 1)
    for idx, raw in enumerate(messages, start=1):
        try:
            message = deserialize_message(raw)
            print(f"{idx}. {message.model_dump()}")
        except Exception as exc:
            print(f"{idx}. <failed to parse> {raw} ({exc})")
    await redis.close()
    await redis.connection_pool.disconnect(inuse_connections=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect Bitrix24 DLQ messages")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to show")
    args = parser.parse_args()
    asyncio.run(main(args.limit))
