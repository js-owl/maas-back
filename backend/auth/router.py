"""
Authentication router
Handles login, logout, and registration endpoints
"""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.core.redis import get_redis
from backend.core.config import BITRIX_ENABLED, REFRESH_COOKIE_NAME
from backend.bitrix24.user_sync import enqueue_user_create
from backend.auth.email_verification import (
    confirm_email,
    get_client_ip,
    send_confirmation_email,
)
from backend.auth.password_recovery import (
    reset_password,
    send_password_recovery_email,
)
from backend.auth.dependencies import ensure_account_accessible
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
    return create_access_token({"sub": str(user.id), "is_admin": user.is_admin})


@router.post('/login', response_model=schemas.LoginResponse, tags=["Authentication"], openapi_extra={"security": []})
async def login(
    login_data: schemas.UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Login user and return access token"""
    user = await authenticate_user(db, login_data.personal_email, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect personal email or password")
    ensure_account_accessible(user)
    access_token = _access_token_for_user(user)
    user_id = str(user.id)
    refresh_token, jti, ttl_seconds = create_refresh_token(user_id, login_data.remember_me)
    await store_refresh_session(redis, jti, user_id, ttl_seconds)
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
    user_id = payload["sub"]
    stored_user_id = await get_refresh_session(redis, jti)
    if stored_user_id != user_id:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session expired or revoked")

    await delete_refresh_session(redis, jti)

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    user = result.scalar_one_or_none()
    if user is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if getattr(user, "status", "active") == "cancelled":
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is cancelled")

    try:
        ensure_account_accessible(user)
    except HTTPException:
        clear_refresh_cookie(response)
        raise

    remember_me = bool(payload.get("remember_me", False))
    new_refresh_token, new_jti, ttl_seconds = create_refresh_token(str(user.id), remember_me)
    await store_refresh_session(redis, new_jti, str(user.id), ttl_seconds)
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


@router.post('/register', response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Register a new user"""
    personal_email = user.personal_email.strip().lower()
    logger.info("Registering user with personal email")
    result = await db.execute(
        select(models.User).where(func.lower(models.User.personal_email) == personal_email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning("Personal email already registered")
        raise HTTPException(status_code=400, detail="Personal email already registered")
    # Always hash password
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        personal_email=personal_email,
        hashed_password=hashed_password,
        is_admin=False,
        user_type="legal",
        status="active",
        email=None,
        full_name=user.full_name,
        personal_phone_number=user.personal_phone_number,
        email_verified=False,
        password_changed_at=models.utcnow(),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info("User created: %s", db_user.id)

    if BITRIX_ENABLED:
        try:
            await enqueue_user_create(db, redis, db_user)
        except Exception:
            logger.exception(
                "Failed to enqueue Bitrix24 user sync for user %s",
                db_user.id,
            )
    return db_user


@router.options('/email/send-confirmation', tags=["Authentication"])
async def send_confirmation_options():
    """Handle CORS preflight for send confirmation email."""
    return Response(status_code=200)


@router.options('/email/confirm', tags=["Authentication"])
async def confirm_email_options():
    """Handle CORS preflight for email confirmation."""
    return Response(status_code=200)


@router.post(
    '/email/send-confirmation',
    response_model=schemas.EmailSendConfirmationResponse,
    tags=["Authentication"],
    openapi_extra={"security": []},
)
async def send_confirmation(
    body: schemas.EmailSendConfirmationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Send email verification link to the given address (public)."""
    client_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("X-Forwarded-For"),
    )
    return await send_confirmation_email(db, redis, body.personal_email, client_ip)


@router.post(
    '/email/confirm',
    response_model=schemas.EmailConfirmResponse,
    tags=["Authentication"],
    openapi_extra={"security": []},
)
async def confirm_email_endpoint(
    body: schemas.EmailConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Confirm email using verification token (public)."""
    client_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("X-Forwarded-For"),
    )
    return await confirm_email(db, redis, body.token, client_ip)


@router.options('/password/send-recovery', tags=["Authentication"])
async def send_password_recovery_options():
    """Handle CORS preflight for send password recovery email."""
    return Response(status_code=200)


@router.options('/password/reset', tags=["Authentication"])
async def reset_password_options():
    """Handle CORS preflight for password reset."""
    return Response(status_code=200)


@router.post(
    '/password/send-recovery',
    response_model=schemas.PasswordSendRecoveryResponse,
    tags=["Authentication"],
    openapi_extra={"security": []},
)
async def send_password_recovery(
    body: schemas.PasswordSendRecoveryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Send password recovery link to the given address (public)."""
    client_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("X-Forwarded-For"),
    )
    return await send_password_recovery_email(db, redis, body.personal_email, client_ip)


@router.post(
    '/password/reset',
    response_model=schemas.PasswordResetResponse,
    tags=["Authentication"],
    openapi_extra={"security": []},
)
async def reset_password_endpoint(
    body: schemas.PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Reset password using recovery token (public)."""
    client_ip = get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("X-Forwarded-For"),
    )
    return await reset_password(db, redis, body.token, body.password, client_ip)
