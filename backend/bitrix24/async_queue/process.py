"""Executor process management for Bitrix24 async queue."""
from __future__ import annotations

import asyncio
import os
import signal
import multiprocessing as mp
from multiprocessing import Process

from fastapi import FastAPI
from redis.asyncio import Redis

from backend.bitrix24.async_queue.executor import executor_loop
from backend.bitrix24.client import BitrixClient
from backend.bitrix24.reverse_sync import run_loop as reverse_sync_run_loop
from backend.core.config import (
    BITRIX24_ACCESS_TOKEN,
    BITRIX24_TIMEOUT,
    BITRIX24_WEBHOOK_URL,
    BITRIX_ENABLED,
    BITRIX_REVERSE_SYNC_ENABLED,
    BITRIX_REVERSE_SYNC_INTERVAL_SECONDS,
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


def run_reverse_sync_worker() -> None:
    """Entry point for the reverse sync process (Bitrix24 → MaaS). Run as a separate process.
    Does not use the direct-sync Redis queue. Set BITRIX_REVERSE_SYNC_ENABLED=true to use.
    """
    if not BITRIX24_WEBHOOK_URL:
        logger.error("BITRIX24_WEBHOOK_URL is not configured; reverse sync cannot start")
        return

    redis = Redis(connection_pool=create_redis_pool())
    client = BitrixClient(
        base_url=BITRIX24_WEBHOOK_URL,
        access_token=BITRIX24_ACCESS_TOKEN,
        timeout=BITRIX24_TIMEOUT,
        verify_tls=BITRIX_VERIFY_TLS,
    )
    asyncio.run(reverse_sync_run_loop(client, redis, interval_seconds=BITRIX_REVERSE_SYNC_INTERVAL_SECONDS))


def start_executor_process(app: FastAPI) -> None:
    """Spawn executor process on application startup."""
    if not BITRIX_ENABLED:
        logger.info("Bitrix24 executor not started (BITRIX_ENABLED=false)")
        return

    try:
        mp.set_start_method("spawn", force=True)
        logger.info("Bitrix24 executor process, start method: spawn")
    except RuntimeError:
        pass

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


def start_reverse_sync_process(app: FastAPI) -> None:
    """Spawn reverse sync process on application startup (when BITRIX_REVERSE_SYNC_ENABLED and webhook are set)."""
    if not BITRIX_REVERSE_SYNC_ENABLED:
        logger.info("Reverse sync process not started (BITRIX_REVERSE_SYNC_ENABLED=false)")
        return

    process = Process(target=run_reverse_sync_worker, name="bitrix24-reverse-sync")
    process.start()
    app.state.reverse_sync_process = process
    logger.info("Bitrix24 reverse sync process started (pid=%s)", process.pid)


def stop_reverse_sync_process(app: FastAPI, timeout: int = 10) -> None:
    """Stop reverse sync process gracefully on application shutdown."""
    process: Process | None = getattr(app.state, "reverse_sync_process", None)
    if process is None:
        return

    try:
        os.kill(process.pid, signal.SIGTERM)
        process.join(timeout=timeout)
        if process.is_alive():
            logger.warning("Reverse sync process did not exit in time; terminating")
            process.terminate()
    except Exception:
        logger.exception("Failed to stop reverse sync process cleanly")
    finally:
        app.state.reverse_sync_process = None
