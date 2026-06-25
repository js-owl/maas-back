"""Password recovery (send recovery email + reset password)."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.auth.email_verification import normalize_email
from backend.auth.service import get_password_hash, revoke_all_refresh_sessions
from backend.bitrix24.auth_email_queue import enqueue_auth_email
from backend.core.config import (
    BITRIX_ENABLED,
    PASSWORD_RECOVERY_ENABLED,
    PASSWORD_RECOVERY_RATE_LIMIT_PER_EMAIL,
    PASSWORD_RECOVERY_RATE_LIMIT_PER_IP,
    PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS,
    PASSWORD_RECOVERY_RESET_URL_TEMPLATE,
    PASSWORD_RECOVERY_SEND_COOLDOWN_SECONDS,
    PASSWORD_RECOVERY_TOKEN_TTL_SECONDS,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REDIS_PREFIX = "auth:password-reset"

SEND_SUCCESS_MESSAGE = "If the email is registered, a password recovery message has been sent."
RESET_SUCCESS_MESSAGE = "Password has been reset."
INVALID_TOKEN_DETAIL = "Invalid or expired recovery link."
DISABLED_DETAIL = "Password recovery is not available."


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


def _rate_limit_reset_ip_key(client_ip: str) -> str:
    return f"{REDIS_PREFIX}:rl:reset:ip:{client_ip}"


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
    window = PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS
    retry = await _increment_rate_limit(
        redis, _rate_limit_email_key(normalized_email), PASSWORD_RECOVERY_RATE_LIMIT_PER_EMAIL, window
    )
    if retry is not None:
        _raise_rate_limited(retry)
    retry = await _increment_rate_limit(
        redis, _rate_limit_send_ip_key(client_ip), PASSWORD_RECOVERY_RATE_LIMIT_PER_IP, window
    )
    if retry is not None:
        _raise_rate_limited(retry)


async def _check_reset_rate_limit(redis: Redis, client_ip: str) -> None:
    window = PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS
    retry = await _increment_rate_limit(
        redis, _rate_limit_reset_ip_key(client_ip), PASSWORD_RECOVERY_RATE_LIMIT_PER_IP, window
    )
    if retry is not None:
        _raise_rate_limited(retry)


async def _cooldown_active(redis: Redis, normalized_email: str) -> bool:
    return bool(await redis.exists(_cooldown_key(normalized_email)))


async def _set_cooldown(redis: Redis, normalized_email: str) -> None:
    await redis.set(_cooldown_key(normalized_email), "1", ex=PASSWORD_RECOVERY_SEND_COOLDOWN_SECONDS)


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
    ttl = PASSWORD_RECOVERY_TOKEN_TTL_SECONDS
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


def build_reset_url(token: str) -> str:
    return PASSWORD_RECOVERY_RESET_URL_TEMPLATE.replace("{token}", token)


async def send_password_recovery_email(
    db: AsyncSession,
    redis: Redis,
    personal_email: str,
    client_ip: str,
) -> schemas.PasswordSendRecoveryResponse:
    if not PASSWORD_RECOVERY_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DISABLED_DETAIL)

    normalized = normalize_email(personal_email)
    await _check_send_rate_limits(redis, normalized, client_ip)

    result = await db.execute(
        select(models.User).where(func.lower(models.User.personal_email) == normalized)
    )
    user = result.scalar_one_or_none()
    if user is None or getattr(user, "status", "active") == "cancelled":
        return schemas.PasswordSendRecoveryResponse(message=SEND_SUCCESS_MESSAGE)

    if await _cooldown_active(redis, normalized):
        return schemas.PasswordSendRecoveryResponse(message=SEND_SUCCESS_MESSAGE)

    token = await _issue_token(redis, user.id)

    if BITRIX_ENABLED:
        try:
            await enqueue_auth_email(
                redis,
                kind="recovery",
                user_id=user.id,
                personal_email=user.personal_email,
                token=token,
                url=build_reset_url(token),
            )
        except Exception:
            logger.exception("Failed to enqueue Bitrix recovery email for user %s", user.id)
            await _delete_token_pair(redis, token, user.id)
            return schemas.PasswordSendRecoveryResponse(message=SEND_SUCCESS_MESSAGE)

    await _set_cooldown(redis, normalized)
    return schemas.PasswordSendRecoveryResponse(message=SEND_SUCCESS_MESSAGE)


async def reset_password(
    db: AsyncSession,
    redis: Redis,
    token: str,
    password: str,
    client_ip: str,
) -> schemas.PasswordResetResponse:
    if not PASSWORD_RECOVERY_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DISABLED_DETAIL)

    if not token or not token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    await _check_reset_rate_limit(redis, client_ip)

    token_stripped = token.strip()
    user_id = await _lookup_user_id(redis, token_stripped)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        await _delete_token_pair(redis, token_stripped)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)

    user.hashed_password = get_password_hash(password)
    user.password_changed_at = models.utcnow()
    user.must_change_password = False
    await db.commit()
    await _delete_token_pair(redis, token_stripped, user.id)
    await revoke_all_refresh_sessions(redis, str(user.id))
    return schemas.PasswordResetResponse(message=RESET_SUCCESS_MESSAGE)
