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
    get_user_by_username as repo_get_user_by_username,
    get_users as repo_get_users,
    update_user as repo_update_user,
    delete_user as repo_delete_user
)


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Create a new user with business logic validation"""
    # Check if username already exists
    existing = await repo_get_user_by_username(db, user.username)
    if existing:
        raise ValueError("Username already registered")
    
    return await repo_create_user(db, user)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get user by ID"""
    return await repo_get_user_by_id(db, user_id)


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    """Get user by username"""
    return await repo_get_user_by_username(db, username)


async def get_users(db: AsyncSession) -> List[models.User]:
    """Get all users"""
    return await repo_get_users(db)


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user with business logic validation"""
    # Check if user exists
    user = await repo_get_user_by_id(db, user_id)
    if not user:
        return None
    
    # If username is being changed, check for conflicts
    if user_update.username and user_update.username != user.username:
        existing = await repo_get_user_by_username(db, user_update.username)
        if existing:
            raise ValueError("Username already taken")
    
    return await repo_update_user(db, user_id, user_update)


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user"""
    return await repo_delete_user(db, user_id)
