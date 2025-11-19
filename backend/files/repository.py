"""
Files repository module
Database operations for file management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models


async def create_file_record(db: AsyncSession, file_data: dict) -> models.FileStorage:
    """Create a new file record in database"""
    db_file = models.FileStorage(**file_data)
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file


async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[models.FileStorage]:
    """Get file record by ID"""
    result = await db.execute(select(models.FileStorage).where(models.FileStorage.id == file_id))
    return result.scalar_one_or_none()


async def get_file_by_filename(db: AsyncSession, filename: str) -> Optional[models.FileStorage]:
    """Get file record by filename"""
    result = await db.execute(select(models.FileStorage).where(models.FileStorage.filename == filename))
    return result.scalar_one_or_none()


async def get_files_by_user(db: AsyncSession, user_id: int) -> List[models.FileStorage]:
    """Get all files uploaded by a user"""
    result = await db.execute(select(models.FileStorage).where(models.FileStorage.uploaded_by == user_id))
    return result.scalars().all()


async def delete_file_record(db: AsyncSession, file_id: int) -> bool:
    """Delete file record from database"""
    file_record = await get_file_by_id(db, file_id)
    if not file_record:
        return False
    
    await db.delete(file_record)
    await db.commit()
    return True


async def update_file_preview(db: AsyncSession, file_id: int, preview_data: dict) -> Optional[models.FileStorage]:
    """Update file record with preview generation results"""
    file_record = await get_file_by_id(db, file_id)
    if not file_record:
        return None
    
    # Update preview fields
    file_record.preview_filename = preview_data.get('preview_filename')
    file_record.preview_path = preview_data.get('preview_path')
    file_record.preview_generated = preview_data.get('preview_generated', False)
    file_record.preview_generation_error = preview_data.get('preview_generation_error')
    
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)
    return file_record


async def get_file_preview_path(db: AsyncSession, file_id: int) -> Optional[str]:
    """Get preview image path for a file"""
    print('===== repo get_file_preview_path', file_id)
    file_record = await get_file_by_id(db, file_id)
    if not file_record or not file_record.preview_generated:
        return None
    return file_record.preview_path
