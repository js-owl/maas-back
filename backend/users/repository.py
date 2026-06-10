"""
Users repository module
Database operations for user management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_
from backend import models, schemas
from backend.core.base_repository import BaseRepository
from backend.core.exceptions import NotFoundException
from backend.auth.service import get_password_hash
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class UserRepository(BaseRepository[models.User]):
    """User repository with specific user operations"""
    
    def __init__(self):
        super().__init__(models.User)
    
    async def get_by_personal_email(self, db: AsyncSession, personal_email: str) -> Optional[models.User]:
        """Get user by personal email."""
        normalized = personal_email.strip().lower()
        try:
            result = await db.execute(
                select(models.User).where(func.lower(models.User.personal_email) == normalized)
            )
            user = result.scalar_one_or_none()
            if user:
                logger.info("[GET_BY_PERSONAL_EMAIL] User ID: %s - Found", user.id)
            else:
                logger.info("[GET_BY_PERSONAL_EMAIL] Not found")
            return user
        except Exception as e:
            logger.error("[GET_BY_PERSONAL_EMAIL] Error: %s", e)
            raise
    
    async def create_user(self, db: AsyncSession, user: schemas.UserCreate) -> models.User:
        """Create a new user with hashed password"""
        try:
            hashed_password = get_password_hash(user.password)
            user_data = user.dict(exclude={'password'})
            user_data['personal_email'] = user_data['personal_email'].strip().lower()
            user_data['hashed_password'] = hashed_password
            user_data.setdefault('status', 'active')
            if 'location' not in user_data or (isinstance(user_data.get('location'), str) and not user_data.get('location').strip()):
                user_data['location'] = None
            
            db_user = await self.create(db, **user_data)
            logger.info(f"[CREATE_USER] User ID: {db_user.id} - Created")
            return db_user
        except Exception as e:
            logger.error(f"[CREATE_USER] Personal email: {user.personal_email} - Error: {e}")
            raise
    
    async def update_user(self, db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> models.User:
        """Update user information with password hashing"""
        try:
            update_data = user_update.dict(exclude_unset=True)
            if 'password' in update_data:
                update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
            
            updated_user = await self.update(db, user_id, **update_data)
            logger.info(f"[UPDATE_USER] User: {user_id} - Updated")
            return updated_user
        except Exception as e:
            logger.error(f"[UPDATE_USER] User: {user_id} - Error: {e}")
            raise


# Create global instance
user_repository = UserRepository()

# Backward compatibility functions
async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Create a new user (backward compatibility)"""
    return await user_repository.create_user(db, user)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get user by ID (backward compatibility)"""
    return await user_repository.get_by_id(db, user_id)


async def get_user_by_personal_email(db: AsyncSession, personal_email: str) -> Optional[models.User]:
    """Get user by personal email."""
    return await user_repository.get_by_personal_email(db, personal_email)


async def get_users(db: AsyncSession) -> List[models.User]:
    """Get all active users (backward compatibility)."""
    result = await db.execute(
        select(models.User).where(
            or_(models.User.status.is_(None), models.User.status != "cancelled")
        )
    )
    return result.scalars().all()


async def get_active_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get active user by ID, excluding cancelled users."""
    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id,
            or_(models.User.status.is_(None), models.User.status != "cancelled"),
        )
    )
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user information (backward compatibility)"""
    try:
        return await user_repository.update_user(db, user_id, user_update)
    except NotFoundException:
        return None


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Soft delete user by setting status to 'cancelled'."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.status = "cancelled"
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return True


async def hard_delete_user(db: AsyncSession, user_id: int) -> bool:
    """Permanently delete user from database."""
    try:
        return await user_repository.delete(db, user_id)
    except NotFoundException:
        return False
