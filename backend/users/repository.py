"""
Users repository module
Database operations for user management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[models.User]:
        """Get user by username"""
        try:
            result = await db.execute(select(models.User).where(models.User.username == username))
            user = result.scalar_one_or_none()
            if user:
                logger.info(f"[GET_BY_USERNAME] User: {username} - Found")
            else:
                logger.info(f"[GET_BY_USERNAME] User: {username} - Not found")
            return user
        except Exception as e:
            logger.error(f"[GET_BY_USERNAME] User: {username} - Error: {e}")
            raise
    
    async def create_user(self, db: AsyncSession, user: schemas.UserCreate) -> models.User:
        """Create a new user with hashed password"""
        try:
            hashed_password = get_password_hash(user.password)
            user_data = user.dict(exclude={'password'})
            user_data['hashed_password'] = hashed_password
            
            db_user = await self.create(db, **user_data)
            logger.info(f"[CREATE_USER] User: {db_user.username} (ID: {db_user.id}) - Created")
            return db_user
        except Exception as e:
            logger.error(f"[CREATE_USER] User: {user.username} - Error: {e}")
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


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    """Get user by username (backward compatibility)"""
    return await user_repository.get_by_username(db, username)


async def get_users(db: AsyncSession) -> List[models.User]:
    """Get all users (backward compatibility)"""
    return await user_repository.get_all(db, skip=0, limit=10000)  # Increase limit to avoid pagination issues


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user information (backward compatibility)"""
    try:
        return await user_repository.update_user(db, user_id, user_update)
    except NotFoundException:
        return None


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user (backward compatibility)"""
    try:
        return await user_repository.delete(db, user_id)
    except NotFoundException:
        return False
