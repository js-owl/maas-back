"""
Users service module
Business logic for user management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.users.repository import (
    create_user as repo_create_user,
    get_user_by_id as repo_get_user_by_id,
    get_user_by_personal_email as repo_get_user_by_personal_email,
    get_users as repo_get_users,
    get_active_user_by_id as repo_get_active_user_by_id,
    update_user as repo_update_user,
    delete_user as repo_delete_user,
    hard_delete_user as repo_hard_delete_user
)


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Create a new user with business logic validation"""
    existing = await repo_get_user_by_personal_email(db, user.personal_email)
    if existing:
        raise ValueError("Personal email already registered")
    
    return await repo_create_user(db, user)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get user by ID"""
    return await repo_get_user_by_id(db, user_id)


async def get_user_by_personal_email(db: AsyncSession, personal_email: str) -> Optional[models.User]:
    """Get user by personal email."""
    return await repo_get_user_by_personal_email(db, personal_email)


async def get_active_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get active user by ID, excluding cancelled users."""
    return await repo_get_active_user_by_id(db, user_id)


async def get_users(db: AsyncSession) -> List[models.User]:
    """Get all users"""
    return await repo_get_users(db)


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user with business logic validation"""
    # Check if user exists
    user = await repo_get_user_by_id(db, user_id)
    if not user:
        return None
    
    return await repo_update_user(db, user_id, user_update)


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Soft delete user by setting status to 'cancelled'."""
    return await repo_delete_user(db, user_id)


async def hard_delete_user(db: AsyncSession, user_id: int) -> bool:
    """Permanently delete user from database."""
    return await repo_hard_delete_user(db, user_id)
