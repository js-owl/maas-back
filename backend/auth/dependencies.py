"""
Authentication dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models
from backend.core.dependencies import get_request_db as get_db
from backend.auth.service import decode_access_token
from typing import Optional

EMAIL_NOT_VERIFIED_DETAIL = (
    "Email address not verified. Please confirm your email before accessing your account."
)


def is_account_accessible(user: models.User) -> bool:
    """Admins may access without verified email; regular users require verification."""
    return bool(user.is_admin or user.email_verified)


def ensure_account_accessible(user: models.User) -> None:
    if not is_account_accessible(user):
        raise HTTPException(status_code=403, detail=EMAIL_NOT_VERIFIED_DETAIL)


def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract token from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return authorization.split(" ")[1]


async def get_current_user(
    token: str = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """Get current user from token"""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if getattr(user, "status", "active") == "cancelled":
        raise HTTPException(status_code=403, detail="User account is cancelled")

    ensure_account_accessible(user)
    return user


async def get_current_admin_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Get current user and verify they are an admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_user


async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[models.User]:
    """Get current user from token if provided, otherwise return None"""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None

    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    user = result.scalar_one_or_none()
    if user is not None and getattr(user, "status", "active") == "cancelled":
        return None
    if user is not None and not is_account_accessible(user):
        return None
    return user
