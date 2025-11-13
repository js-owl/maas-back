"""
Base repository pattern
Provides common CRUD operations for all repository classes
"""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase
from backend.core.exceptions import NotFoundException
from backend.utils.logging import get_logger

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get_by_id(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get entity by ID"""
        try:
            result = await db.execute(select(self.model).where(self.model.id == id))
            entity = result.scalar_one_or_none()
            if entity:
                logger.info(f"[GET] {self.model.__name__}: {id} - Found")
            else:
                logger.info(f"[GET] {self.model.__name__}: {id} - Not found")
            return entity
        except Exception as e:
            logger.error(f"[GET] {self.model.__name__}: {id} - Error: {e}")
            raise
    
    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination"""
        try:
            result = await db.execute(
                select(self.model).offset(skip).limit(limit)
            )
            entities = result.scalars().all()
            logger.info(f"[GET_ALL] {self.model.__name__} - Found {len(entities)} entities")
            return list(entities)
        except Exception as e:
            logger.error(f"[GET_ALL] {self.model.__name__} - Error: {e}")
            raise
    
    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        """Create new entity"""
        try:
            entity = self.model(**kwargs)
            db.add(entity)
            await db.flush()  # Flush to get the ID
            await db.refresh(entity)
            logger.info(f"[CREATE] {self.model.__name__}: {entity.id} - Created")
            return entity
        except Exception as e:
            logger.error(f"[CREATE] {self.model.__name__} - Error: {e}")
            raise
    
    async def update(self, db: AsyncSession, id: int, **kwargs) -> Optional[ModelType]:
        """Update entity by ID"""
        try:
            # First check if entity exists
            entity = await self.get_by_id(db, id)
            if not entity:
                raise NotFoundException(f"{self.model.__name__} with id {id} not found")
            
            # Update fields
            for field, value in kwargs.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            logger.info(f"[UPDATE] {self.model.__name__}: {id} - Updated")
            return entity
        except Exception as e:
            logger.error(f"[UPDATE] {self.model.__name__}: {id} - Error: {e}")
            raise
    
    async def delete(self, db: AsyncSession, id: int) -> bool:
        """Delete entity by ID"""
        try:
            # First check if entity exists
            entity = await self.get_by_id(db, id)
            if not entity:
                raise NotFoundException(f"{self.model.__name__} with id {id} not found")
            
            await db.delete(entity)
            await db.flush()
            logger.info(f"[DELETE] {self.model.__name__}: {id} - Deleted")
            return True
        except Exception as e:
            logger.error(f"[DELETE] {self.model.__name__}: {id} - Error: {e}")
            raise
    
    async def exists(self, db: AsyncSession, id: int) -> bool:
        """Check if entity exists by ID"""
        try:
            entity = await self.get_by_id(db, id)
            return entity is not None
        except Exception as e:
            logger.error(f"[EXISTS] {self.model.__name__}: {id} - Error: {e}")
            raise
    
    async def count(self, db: AsyncSession) -> int:
        """Count total entities"""
        try:
            result = await db.execute(select(self.model))
            count = len(result.scalars().all())
            logger.info(f"[COUNT] {self.model.__name__} - Total: {count}")
            return count
        except Exception as e:
            logger.error(f"[COUNT] {self.model.__name__} - Error: {e}")
            raise
