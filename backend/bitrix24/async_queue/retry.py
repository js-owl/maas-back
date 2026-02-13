"""Retry logic and error classification for async queue processing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx

from backend.bitrix24.exceptions import BitrixAPIError
from backend.bitrix24.async_queue.message import QueueMessage

ErrorClass = Literal["transient", "permanent", "rate_limit"]


def calculate_retry_delay(attempt: int, base: int = 5, factor: int = 2, max_delay: int = 300) -> int:
    """Calculate exponential backoff delay with cap."""
    delay = base * (factor ** attempt)
    return min(delay, max_delay)


def classify_error(error: Exception) -> ErrorClass:
    """Classify errors into transient, permanent, or rate_limit."""
    if isinstance(error, BitrixAPIError):
        if error.status_code == 429 or error.code == "QUERY_LIMIT_EXCEEDED":
            return "rate_limit"
        if error.status_code is not None:
            if 500 <= error.status_code < 600:
                return "transient"
            if 400 <= error.status_code < 500:
                return "permanent"
        return "permanent"

    if isinstance(error, (httpx.TimeoutException, httpx.TransportError, TimeoutError)):
        return "transient"

    return "permanent"


def should_retry(attempt: int, error: Exception) -> bool:
    """Return True if error is transient and attempts remain."""
    if attempt >= 5:
        return False
    return classify_error(error) in {"transient", "rate_limit"}


def rate_limit_delay(error: BitrixAPIError) -> int:
    """Compute retry delay for rate limiting (min 60s, respects Retry-After)."""
    retry_after = None
    if error.headers:
        value = error.headers.get("Retry-After")
        if value:
            try:
                retry_after = int(value)
            except ValueError:
                retry_after = None
    base_delay = 60
    if retry_after is None:
        return base_delay
    return max(base_delay, retry_after)


def retry_message(message: QueueMessage, delay_seconds: int) -> QueueMessage:
    """Increment attempt and set delay_until for retry."""
    message.attempt += 1
    message.delay_until = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    return message


__all__ = [
    "calculate_retry_delay",
    "classify_error",
    "should_retry",
    "rate_limit_delay",
    "retry_message",
]
