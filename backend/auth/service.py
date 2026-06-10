"""
Authentication service module
JWT token generation/validation and password hashing
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import uuid4
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from starlette.responses import Response
import warnings

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", message=".*bcrypt.*")
from backend.utils.logging import get_logger
from backend.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_COOKIE_DOMAIN,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_COOKIE_SAMESITE,
    REFRESH_COOKIE_SECURE,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_EXPIRE_MINUTES_SESSION,
    REFRESH_TOKEN_SECRET,
    SECRET_KEY,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
REFRESH_REDIS_PREFIX = "auth:refresh:"
logger = get_logger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "token_use": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_use", "access") != "access":
            return None
        return payload
    except JWTError:
        return None


def get_refresh_ttl_seconds(remember_me: bool) -> int:
    """Return refresh token TTL in seconds for the requested persistence mode."""
    if remember_me:
        return REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    return REFRESH_TOKEN_EXPIRE_MINUTES_SESSION * 60


def create_refresh_token(user_id: str, remember_me: bool) -> Tuple[str, str, int]:
    """Create a signed refresh JWT with a unique session identifier."""
    jti = str(uuid4())
    ttl_seconds = get_refresh_ttl_seconds(remember_me)
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "jti": jti,
        "token_use": "refresh",
        "remember_me": remember_me,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    token = jwt.encode(payload, REFRESH_TOKEN_SECRET, algorithm=ALGORITHM)
    return token, jti, ttl_seconds


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate a refresh JWT."""
    try:
        payload = jwt.decode(token, REFRESH_TOKEN_SECRET, algorithms=[ALGORITHM])
        if payload.get("token_use") != "refresh":
            return None
        if not payload.get("jti") or not payload.get("sub"):
            return None
        return payload
    except JWTError:
        return None


def get_refresh_session_key(jti: str) -> str:
    """Build the Redis key for a refresh session."""
    return f"{REFRESH_REDIS_PREFIX}{jti}"


async def store_refresh_session(redis: Redis, jti: str, user_id: str, ttl_seconds: int) -> None:
    """Store a refresh session allowlist entry in Redis."""
    await redis.set(get_refresh_session_key(jti), user_id, ex=ttl_seconds)


async def get_refresh_session(redis: Redis, jti: str) -> Optional[str]:
    """Fetch the user id bound to a refresh session."""
    value = await redis.get(get_refresh_session_key(jti))
    return value if isinstance(value, str) else None


async def delete_refresh_session(redis: Redis, jti: str) -> None:
    """Remove a refresh session from Redis."""
    await redis.delete(get_refresh_session_key(jti))


async def revoke_all_refresh_sessions(redis: Redis, user_id: str) -> int:
    """Remove all refresh allowlist entries for a user id. Returns count deleted."""
    revoked = 0
    async for key in redis.scan_iter(match=f"{REFRESH_REDIS_PREFIX}*"):
        value = await redis.get(key)
        if value is None:
            continue
        if isinstance(value, bytes):
            value = value.decode()
        if value == user_id:
            await redis.delete(key)
            revoked += 1
    if revoked:
        logger.info("Revoked %s refresh session(s) for user %s", revoked, user_id)
    return revoked


def issue_refresh_cookie(
    response: Response,
    refresh_token: str,
    remember_me: bool,
    ttl_seconds: int,
) -> None:
    """Attach the refresh token cookie to a response."""
    cookie_kwargs = {
        "key": REFRESH_COOKIE_NAME,
        "value": refresh_token,
        "path": REFRESH_COOKIE_PATH,
        "httponly": True,
        "secure": REFRESH_COOKIE_SECURE,
        "samesite": REFRESH_COOKIE_SAMESITE,
    }
    if REFRESH_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = REFRESH_COOKIE_DOMAIN
    if remember_me:
        cookie_kwargs["max_age"] = ttl_seconds
    response.set_cookie(**cookie_kwargs)


def clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie using the configured attributes."""
    cookie_kwargs = {
        "key": REFRESH_COOKIE_NAME,
        "path": REFRESH_COOKIE_PATH,
        "httponly": True,
        "secure": REFRESH_COOKIE_SECURE,
        "samesite": REFRESH_COOKIE_SAMESITE,
    }
    if REFRESH_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = REFRESH_COOKIE_DOMAIN
    response.delete_cookie(**cookie_kwargs)


async def authenticate_user(db, personal_email: str, password: str):
    """Authenticate a user with personal email and password."""
    from sqlalchemy import func, select
    from backend import models

    normalized = personal_email.strip().lower()
    result = await db.execute(
        select(models.User).where(func.lower(models.User.personal_email) == normalized)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if getattr(user, "status", "active") == "cancelled":
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
