"""Executor process management for Bitrix24 async queue."""
from __future__ import annotations

import asyncio
import os
import signal
from multiprocessing import Process

from fastapi import FastAPI
from redis.asyncio import Redis

from backend.bitrix24.async_queue.executor import executor_loop
from backend.bitrix24.client import BitrixClient
from backend.core.config import (
    BITRIX24_ACCESS_TOKEN,
    BITRIX24_TIMEOUT,
    BITRIX24_WEBHOOK_URL,
    BITRIX_ENABLED,
    BITRIX_VERIFY_TLS,
)
from backend.core.redis import create_redis_pool
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def run_executor() -> None:
    """Entry point for the executor process."""
    if not BITRIX24_WEBHOOK_URL:
        logger.error("BITRIX24_WEBHOOK_URL is not configured; executor cannot start")
        return

    redis = Redis(connection_pool=create_redis_pool())
    client = BitrixClient(
        base_url=BITRIX24_WEBHOOK_URL,
        access_token=BITRIX24_ACCESS_TOKEN,
        timeout=BITRIX24_TIMEOUT,
        verify_tls=BITRIX_VERIFY_TLS,
    )
    asyncio.run(executor_loop(redis, client))


def start_executor_process(app: FastAPI) -> None:
    """Spawn executor process on application startup."""
    if not BITRIX_ENABLED:
        logger.info("Bitrix24 executor not started (BITRIX_ENABLED=false)")
        return

    process = Process(target=run_executor, name="bitrix24-executor")
    process.start()
    app.state.executor_process = process
    logger.info("Bitrix24 executor process started (pid=%s)", process.pid)


def stop_executor_process(app: FastAPI, timeout: int = 10) -> None:
    """Stop executor process gracefully on application shutdown."""
    process: Process | None = getattr(app.state, "executor_process", None)
    if process is None:
        return

    try:
        os.kill(process.pid, signal.SIGTERM)
        process.join(timeout=timeout)
        if process.is_alive():
            logger.warning("Executor process did not exit in time; terminating")
            process.terminate()
    except Exception:
        logger.exception("Failed to stop executor process cleanly")
    finally:
        app.state.executor_process = None
