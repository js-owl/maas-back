"""
Authentication router
Handles login, logout, and registration endpoints
"""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, status, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.core.redis import get_redis
from backend.core.config import BITRIX_ENABLED, REFRESH_COOKIE_NAME
from backend.bitrix24.user_sync import enqueue_user_create
from backend.auth.service import (
    authenticate_user,
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    delete_refresh_session,
    get_password_hash,
    get_refresh_session,
    issue_refresh_cookie,
    store_refresh_session,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/login', tags=["Authentication"])
async def login_options():
    """Handle CORS preflight requests for login"""
    return Response(status_code=200)

@router.options('/logout', tags=["Authentication"])
async def logout_options():
    """Handle CORS preflight requests for logout"""
    return Response(status_code=200)


@router.options('/refresh', tags=["Authentication"])
async def refresh_options():
    """Handle CORS preflight requests for refresh"""
    return Response(status_code=200)


def _access_token_for_user(user: models.User) -> str:
    return create_access_token({"sub": user.username, "is_admin": user.is_admin})


@router.post('/login', response_model=schemas.LoginResponse, tags=["Authentication"], openapi_extra={"security": []})
async def login(
    login_data: schemas.UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Login user and return access token"""
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = _access_token_for_user(user)
    refresh_token, jti, ttl_seconds = create_refresh_token(user.username, login_data.remember_me)
    await store_refresh_session(redis, jti, user.username, ttl_seconds)
    issue_refresh_cookie(response, refresh_token, login_data.remember_me, ttl_seconds)
    return schemas.LoginResponse(
        access_token=access_token, 
        token_type="bearer", 
        must_change_password=user.must_change_password
    )


@router.post('/refresh', response_model=schemas.RefreshResponse, tags=["Authentication"], openapi_extra={"security": []})
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Rotate refresh token from cookie and return a new access token."""
    if not refresh_token:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    payload = decode_refresh_token(refresh_token)
    if payload is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload["jti"]
    username = payload["sub"]
    stored_username = await get_refresh_session(redis, jti)
    if stored_username != username:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session expired or revoked")

    await delete_refresh_session(redis, jti)

    result = await db.execute(select(models.User).where(models.User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if getattr(user, "status", "active") == "cancelled":
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is cancelled")

    remember_me = bool(payload.get("remember_me", False))
    new_refresh_token, new_jti, ttl_seconds = create_refresh_token(user.username, remember_me)
    await store_refresh_session(redis, new_jti, user.username, ttl_seconds)
    issue_refresh_cookie(response, new_refresh_token, remember_me, ttl_seconds)

    return schemas.RefreshResponse(
        access_token=_access_token_for_user(user),
        token_type="bearer",
        must_change_password=user.must_change_password,
    )


@router.post('/logout', response_model=schemas.LogoutResponse, tags=["Authentication"], openapi_extra={"security": []})
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
    redis: Redis = Depends(get_redis),
):
    """Logout user by invalidating refresh session and clearing cookie."""
    if refresh_token:
        payload = decode_refresh_token(refresh_token)
        if payload and payload.get("jti"):
            await delete_refresh_session(redis, payload["jti"])
            logger.info("Refresh session logged out for user: %s", payload.get("sub"))

    clear_refresh_cookie(response)
    return schemas.LogoutResponse(
        message="Successfully logged out", 
        detail="Refresh session invalidated and cookie cleared"
    )


# CORS preflight handler for register
@router.options('/register', tags=["Authentication"])
async def register_options():
    """Handle CORS preflight requests for register endpoint"""
    return Response(status_code=200)


@router.post('/register', response_model=schemas.UserOut, tags=["Authentication"])
async def register_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Register a new user"""
    logger.info(f"Registering user: {user.username}")
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning(f"Username already registered: {user.username}")
        raise HTTPException(status_code=400, detail="Username already registered")
    # Always hash password
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username, 
        hashed_password=hashed_password, 
        is_admin=False,
        user_type=user.user_type,
        status="active",
        email=user.email,
        full_name=user.full_name,
        city=user.city,
        company=user.company,
        phone_number=user.phone_number,
        personal_phone_number=user.personal_phone_number,
        payment_card_number=user.payment_card_number,
        location=(user.location.strip() if user.location else None),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"User created: {db_user.id} - {db_user.username}")

    if BITRIX_ENABLED:
        try:
            await enqueue_user_create(db, redis, db_user)
        except Exception:
            logger.exception(
                "Failed to enqueue Bitrix24 user sync for user %s",
                db_user.id,
            )
    return db_user
