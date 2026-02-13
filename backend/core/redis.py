"""Redis connection management for the application."""
from fastapi import FastAPI, Request
from redis.asyncio import ConnectionPool, Redis

from backend.core.config import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_POOL_MAX_CONNECTIONS,
    REDIS_PORT,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def create_redis_pool() -> ConnectionPool:
    """Create a shared Redis connection pool."""
    return ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        max_connections=REDIS_POOL_MAX_CONNECTIONS,
        decode_responses=True,
    )


async def init_redis(app: FastAPI) -> None:
    """Initialize Redis client and attach to app state."""
    pool = create_redis_pool()
    app.state.redis = Redis(connection_pool=pool)
    try:
        await app.state.redis.ping()
        logger.info("Redis connection initialized")
    except Exception:
        logger.exception("Failed to connect to Redis during startup")
        raise


async def close_redis(app: FastAPI) -> None:
    """Close Redis client and disconnect connection pool."""
    redis = getattr(app.state, "redis", None)
    if redis is None:
        return
    try:
        await redis.close()
        await redis.connection_pool.disconnect(inuse_connections=True)
        logger.info("Redis connection closed")
    except Exception:
        logger.exception("Failed to close Redis connection cleanly")


def get_redis(request: Request) -> Redis:
    """Return the Redis client from app state."""
    return request.app.state.redis


__all__ = ["create_redis_pool", "init_redis", "close_redis", "get_redis"]
