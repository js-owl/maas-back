"""
Documents repository module
Database operations for document management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models


async def create_document(db: AsyncSession, document_data: dict) -> models.DocumentStorage:
    """Create a new document record"""
    db_document = models.DocumentStorage(**document_data)
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document


async def get_document_by_id(db: AsyncSession, document_id: int) -> Optional[models.DocumentStorage]:
    """Get document by ID"""
    result = await db.execute(select(models.DocumentStorage).where(models.DocumentStorage.id == document_id))
    return result.scalar_one_or_none()


async def get_documents_by_ids(db: AsyncSession, document_ids: List[int]) -> List[models.DocumentStorage]:
    """Get multiple documents by their IDs"""
    if not document_ids:
        return []
    result = await db.execute(select(models.DocumentStorage).where(models.DocumentStorage.id.in_(document_ids)))
    return result.scalars().all()


async def get_documents_by_user(db: AsyncSession, user_id: int) -> List[models.DocumentStorage]:
    """Get all documents for a specific user"""
    result = await db.execute(select(models.DocumentStorage).where(models.DocumentStorage.uploaded_by == user_id))
    return result.scalars().all()


async def get_documents_by_category(db: AsyncSession, category: str) -> List[models.DocumentStorage]:
    """Get all documents by category"""
    result = await db.execute(select(models.DocumentStorage).where(models.DocumentStorage.document_category == category))
    return result.scalars().all()


async def get_document_by_filename(db: AsyncSession, filename: str) -> Optional[models.DocumentStorage]:
    """Get document by filename"""
    result = await db.execute(select(models.DocumentStorage).where(models.DocumentStorage.filename == filename))
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete document record"""
    document = await get_document_by_id(db, document_id)
    if not document:
        return False
    
    await db.delete(document)
    await db.commit()
    return True
