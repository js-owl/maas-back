"""
Authentication router
Handles login, logout, and registration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.service import authenticate_user, create_access_token, get_password_hash
from backend.auth.dependencies import get_current_user
from backend.bitrix.client import bitrix_client
from backend.users.repository import get_user_by_id
from backend.database import get_db as get_db_session
from backend.utils.logging import get_logger
import asyncio

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

@router.post('/login', response_model=schemas.LoginResponse, tags=["Authentication"])
async def login(login_data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return access token"""
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username, "is_admin": user.is_admin})
    return schemas.LoginResponse(
        access_token=access_token, 
        token_type="bearer", 
        must_change_password=user.must_change_password
    )


@router.post('/logout', response_model=schemas.LogoutResponse, tags=["Authentication"])
async def logout(current_user: models.User = Depends(get_current_user)):
    """Logout user (invalidate token on client side)"""
    # Note: JWT tokens are stateless, so server-side invalidation requires a blacklist
    # For now, we'll return a success message and let the client handle token removal
    logger.info(f"User logout: {current_user.username}")
    return schemas.LogoutResponse(
        message="Successfully logged out", 
        detail="Token should be removed from client storage"
    )


# CORS preflight handler for register
@router.options('/register', tags=["Authentication"])
async def register_options():
    """Handle CORS preflight requests for register endpoint"""
    return Response(status_code=200)


@router.post('/register', response_model=schemas.UserOut, tags=["Authentication"])
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
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
        email=user.email,
        full_name=user.full_name,
        city=user.city,
        company=user.company,
        phone_number=user.phone_number,
        payment_card_number=user.payment_card_number
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"User created: {db_user.id} - {db_user.username}")
    # Bitrix: queue contact creation via Redis
    try:
        from backend.bitrix.sync_service import bitrix_sync_service
        await bitrix_sync_service.queue_contact_creation(db, db_user.id)
    except Exception as e:
        logger.warning(f"Failed to queue Bitrix contact creation for user {db_user.id}: {e}")
        # Don't fail user registration if Bitrix sync fails
    return db_user
