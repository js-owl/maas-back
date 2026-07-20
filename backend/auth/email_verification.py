"""Email verification during registration (send + confirm)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.auth.email_templates import render_auth_email_template
from backend.auth.smtp_sender import send_auth_email
from backend.core.config import (
    EMAIL_VERIFICATION_BITRIX_SUBJECT,
    EMAIL_VERIFICATION_CONFIRM_URL_TEMPLATE,
    EMAIL_VERIFICATION_ENABLED,
    EMAIL_VERIFICATION_RATE_LIMIT_PER_EMAIL,
    EMAIL_VERIFICATION_RATE_LIMIT_PER_IP,
    EMAIL_VERIFICATION_RATE_LIMIT_WINDOW_SECONDS,
    EMAIL_VERIFICATION_SEND_COOLDOWN_SECONDS,
    EMAIL_VERIFICATION_TOKEN_TTL_SECONDS,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REDIS_PREFIX = "auth:email-verify"

SEND_SUCCESS_MESSAGE = "If the email is registered, a confirmation message has been sent."
CONFIRM_SUCCESS_MESSAGE = "Email confirmed."
INVALID_TOKEN_DETAIL = "Invalid or expired confirmation link."
DISABLED_DETAIL = "Email verification is not available."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_client_ip(client_host: Optional[str], forwarded_for: Optional[str]) -> str:
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return client_host or "unknown"


def _token_key(token: str) -> str:
    return f"{REDIS_PREFIX}:token:{token}"


def _user_key(user_id: int) -> str:
    return f"{REDIS_PREFIX}:user:{user_id}"


def _cooldown_key(normalized_email: str) -> str:
    return f"{REDIS_PREFIX}:sent:{normalized_email}"


def _rate_limit_email_key(normalized_email: str) -> str:
    return f"{REDIS_PREFIX}:rl:email:{normalized_email}"


def _rate_limit_send_ip_key(client_ip: str) -> str:
    return f"{REDIS_PREFIX}:rl:ip:{client_ip}"


def _rate_limit_confirm_ip_key(client_ip: str) -> str:
    return f"{REDIS_PREFIX}:rl:confirm:ip:{client_ip}"


async def _increment_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> Optional[int]:
    """Return retry-after seconds when limit exceeded, else None."""
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    if count > limit:
        ttl = await redis.ttl(key)
        return max(int(ttl), 1) if ttl and ttl > 0 else window_seconds
    return None


def _raise_rate_limited(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please try again later.",
        headers={"Retry-After": str(retry_after)},
    )


async def _check_send_rate_limits(redis: Redis, normalized_email: str, client_ip: str) -> None:
    window = EMAIL_VERIFICATION_RATE_LIMIT_WINDOW_SECONDS
    retry = await _increment_rate_limit(
        redis, _rate_limit_email_key(normalized_email), EMAIL_VERIFICATION_RATE_LIMIT_PER_EMAIL, window
    )
    if retry is not None:
        _raise_rate_limited(retry)
    retry = await _increment_rate_limit(
        redis, _rate_limit_send_ip_key(client_ip), EMAIL_VERIFICATION_RATE_LIMIT_PER_IP, window
    )
    if retry is not None:
        _raise_rate_limited(retry)


async def _check_confirm_rate_limit(redis: Redis, client_ip: str) -> None:
    window = EMAIL_VERIFICATION_RATE_LIMIT_WINDOW_SECONDS
    retry = await _increment_rate_limit(
        redis, _rate_limit_confirm_ip_key(client_ip), EMAIL_VERIFICATION_RATE_LIMIT_PER_IP, window
    )
    if retry is not None:
        _raise_rate_limited(retry)


async def _cooldown_active(redis: Redis, normalized_email: str) -> bool:
    return bool(await redis.exists(_cooldown_key(normalized_email)))


async def _set_cooldown(redis: Redis, normalized_email: str) -> None:
    await redis.set(_cooldown_key(normalized_email), "1", ex=EMAIL_VERIFICATION_SEND_COOLDOWN_SECONDS)


async def _revoke_user_token(redis: Redis, user_id: int) -> None:
    user_key = _user_key(user_id)
    old_token = await redis.get(user_key)
    if old_token:
        if isinstance(old_token, bytes):
            old_token = old_token.decode()
        await redis.delete(_token_key(old_token))
    await redis.delete(user_key)


async def _issue_token(redis: Redis, user_id: int) -> str:
    await _revoke_user_token(redis, user_id)
    token = secrets.token_urlsafe(32)
    ttl = EMAIL_VERIFICATION_TOKEN_TTL_SECONDS
    await redis.set(_token_key(token), str(user_id), ex=ttl)
    await redis.set(_user_key(user_id), token, ex=ttl)
    return token


async def _delete_token_pair(redis: Redis, token: str, user_id: Optional[int] = None) -> None:
    await redis.delete(_token_key(token))
    if user_id is not None:
        await redis.delete(_user_key(user_id))


async def _lookup_user_id(redis: Redis, token: str) -> Optional[int]:
    raw = await redis.get(_token_key(token))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def build_confirmation_url(token: str) -> str:
    return EMAIL_VERIFICATION_CONFIRM_URL_TEMPLATE.replace("{token}", token)


async def send_confirmation_email(
    db: AsyncSession,
    redis: Redis,
    personal_email: str,
    client_ip: str,
) -> schemas.EmailSendConfirmationResponse:
    if not EMAIL_VERIFICATION_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DISABLED_DETAIL)

    normalized = normalize_email(personal_email)
    await _check_send_rate_limits(redis, normalized, client_ip)

    result = await db.execute(
        select(models.User).where(func.lower(models.User.personal_email) == normalized)
    )
    user = result.scalar_one_or_none()
    if user is None or user.email_verified:
        return schemas.EmailSendConfirmationResponse(message=SEND_SUCCESS_MESSAGE)

    if await _cooldown_active(redis, normalized):
        return schemas.EmailSendConfirmationResponse(message=SEND_SUCCESS_MESSAGE)

    token = await _issue_token(redis, user.id)

    try:
        html_body = render_auth_email_template(
            "confirmation",
            action_url=build_confirmation_url(token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=EMAIL_VERIFICATION_TOKEN_TTL_SECONDS),
        )
        await send_auth_email(
            to=user.personal_email,
            subject=EMAIL_VERIFICATION_BITRIX_SUBJECT,
            html_body=html_body,
        )
    except Exception:
        logger.exception("Failed to send confirmation email for user %s", user.id)
        await _delete_token_pair(redis, token, user.id)
        return schemas.EmailSendConfirmationResponse(message=SEND_SUCCESS_MESSAGE)

    await _set_cooldown(redis, normalized)
    return schemas.EmailSendConfirmationResponse(message=SEND_SUCCESS_MESSAGE)


async def confirm_email(
    db: AsyncSession,
    redis: Redis,
    token: str,
    client_ip: str,
) -> schemas.EmailConfirmResponse:
    if not EMAIL_VERIFICATION_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DISABLED_DETAIL)

    if not token or not token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    await _check_confirm_rate_limit(redis, client_ip)

    user_id = await _lookup_user_id(redis, token.strip())
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await _delete_token_pair(redis, token.strip())
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    if user.email_verified:
        await _delete_token_pair(redis, token.strip(), user.id)
        return schemas.EmailConfirmResponse(message=CONFIRM_SUCCESS_MESSAGE, email_verified=True)

    user.email_verified = True
    user.email_verified_at = models.utcnow()
    await db.commit()
    await _delete_token_pair(redis, token.strip(), user.id)
    return schemas.EmailConfirmResponse(message=CONFIRM_SUCCESS_MESSAGE, email_verified=True)
