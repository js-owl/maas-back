import json
from typing import Any, Dict, Optional
from uuid import uuid4

from redis.asyncio import Redis

BASKET_TTL = 604800


def _basket_key(user_id: int) -> str:
    return f"basket:{user_id}"


async def add_item(redis: Redis, user_id: int, item_payload: Dict[str, Any]) -> str:
    item_id = str(uuid4())
    key = _basket_key(user_id)
    await redis.hset(key, item_id, json.dumps(item_payload))
    await redis.expire(key, BASKET_TTL)
    return item_id


async def get_all_items(redis: Redis, user_id: int) -> Dict[str, Dict[str, Any]]:
    key = _basket_key(user_id)
    raw_items = await redis.hgetall(key)
    items: Dict[str, Dict[str, Any]] = {}
    for item_id, payload in raw_items.items():
        try:
            items[item_id] = json.loads(payload)
        except json.JSONDecodeError:
            continue
    return items


async def get_item(redis: Redis, user_id: int, item_id: str) -> Optional[Dict[str, Any]]:
    key = _basket_key(user_id)
    raw_payload = await redis.hget(key, item_id)
    if raw_payload is None:
        return None
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return None


async def update_item(
    redis: Redis,
    user_id: int,
    item_id: str,
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    key = _basket_key(user_id)
    current = await get_item(redis, user_id, item_id)
    if current is None:
        raise KeyError(item_id)

    current.update({k: v for k, v in patch.items() if v is not None})
    await redis.hset(key, item_id, json.dumps(current))
    await redis.expire(key, BASKET_TTL)
    return current


async def delete_item(redis: Redis, user_id: int, item_id: str) -> None:
    key = _basket_key(user_id)
    deleted = await redis.hdel(key, item_id)
    if deleted == 0:
        raise KeyError(item_id)
    await redis.expire(key, BASKET_TTL)


async def clear_basket(redis: Redis, user_id: int) -> None:
    key = _basket_key(user_id)
    await redis.delete(key)
