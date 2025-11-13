"""
Files service module
Business logic for file upload, download, and preview generation
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.files.repository import (
    create_file_record as repo_create_file_record,
    get_file_by_id as repo_get_file_by_id,
    get_file_by_filename as repo_get_file_by_filename,
    get_files_by_user as repo_get_files_by_user,
    delete_file_record as repo_delete_file_record,
    update_file_preview as repo_update_file_preview,
    get_file_preview_path as repo_get_file_preview_path
)
from backend.files.storage import file_storage
from backend.files.preview import preview_generator
from backend.utils.logging import get_logger
import asyncio
from pathlib import Path

logger = get_logger(__name__)


async def upload_file_from_base64(
    db: AsyncSession, 
    file_name: str, 
    file_data: str, 
    file_type: str,
    user_id: int, 
) -> models.FileStorage:
    """Upload file from base64 encoded data"""
    try:
        # Save file to storage
        file_metadata = await file_storage.save_file_from_base64(
            file_name, file_data, user_id
        )
        
        # Create database record
        db_file = await repo_create_file_record(db, file_metadata)
        
        # Generate preview asynchronously
        asyncio.create_task(
            generate_preview_async(db_file.id, file_metadata['file_path'], file_name)
        )
        
        logger.info(f"File uploaded successfully: {file_name} (ID: {db_file.id})")
        return db_file
        
    except Exception as e:
        logger.error(f"Error uploading file {file_name}: {e}")
        raise




async def get_file_by_id(db: AsyncSession, file_id: int) -> Optional[models.FileStorage]:
    """Get file by ID"""
    return await repo_get_file_by_id(db, file_id)


async def get_file_by_filename(db: AsyncSession, filename: str) -> Optional[models.FileStorage]:
    """Get file by filename"""
    return await repo_get_file_by_filename(db, filename)


async def get_files_by_user(db: AsyncSession, user_id: int) -> List[models.FileStorage]:
    """Get all files uploaded by a user"""
    return await repo_get_files_by_user(db, user_id)


async def delete_file(db: AsyncSession, file_id: int) -> bool:
    """Delete file and its storage"""
    file_record = await repo_get_file_by_id(db, file_id)
    if not file_record:
        return False
    
    # Delete from storage
    if file_record.filename:
        file_storage.delete_file(file_record.filename)
    
    # Delete preview if exists
    if file_record.preview_filename:
        preview_path = preview_generator.get_preview_path(file_record.preview_filename)
        if preview_path and preview_path.exists():
            preview_path.unlink()
    
    # Delete database record
    return await repo_delete_file_record(db, file_id)


async def get_file_download_path(file_record: models.FileStorage) -> Optional[Path]:
    """Get file path for download"""
    if not file_record or not file_record.file_path:
        return None
    
    # Convert Windows-style paths to Unix-style and ensure absolute path
    normalized_path = file_record.file_path.replace('\\', '/')
    
    # If it's a relative path, make it absolute from /app
    if not normalized_path.startswith('/'):
        file_path = Path('/app') / normalized_path
    else:
        file_path = Path(normalized_path)
    
    if file_path.exists():
        return file_path
    
    return None


async def get_file_preview_path(db: AsyncSession, file_id: int) -> Optional[Path]:
    """Get preview image path for a file"""
    preview_path_str = await repo_get_file_preview_path(db, file_id)
    if not preview_path_str:
        return None
    
    preview_path = Path(preview_path_str)
    return preview_path if preview_path.exists() else None


async def regenerate_preview(db: AsyncSession, file_id: int) -> bool:
    """Regenerate preview for a file"""
    try:
        file_record = await repo_get_file_by_id(db, file_id)
        if not file_record or not file_record.file_path:
            return False
        
        # Generate new preview
        preview_data = await preview_generator.generate_preview(
            Path(file_record.file_path), 
            file_record.original_filename or file_record.filename
        )
        
        if preview_data:
            # Update database record
            await repo_update_file_preview(db, file_id, preview_data)
            logger.info(f"Preview regenerated for file {file_id}")
            return True
        else:
            logger.warning(f"Failed to regenerate preview for file {file_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error regenerating preview for file {file_id}: {e}")
        return False


async def generate_preview_async(file_id: int, model_path: str, original_filename: str):
    """Generate preview image asynchronously after file upload"""
    try:
        logger.info(f"Starting preview generation for file {file_id}: {original_filename}")
        
        # Generate preview
        preview_data = await preview_generator.generate_preview(
            Path(model_path), 
            original_filename
        )
        
        if preview_data:
            # Update database with preview info
            from backend.core.dependencies import get_db
            async for session in get_db():
                await repo_update_file_preview(session, file_id, preview_data)
                logger.info(f"Preview generation completed for file {file_id}: {preview_data.get('preview_generated', False)}")
                break
        else:
            logger.warning(f"Preview generation failed for file {file_id}")
            
    except Exception as e:
        logger.error(f"Error in async preview generation for file {file_id}: {e}")


async def get_demo_files(db: AsyncSession) -> List[models.FileStorage]:
    """Get demo files (IDs 1-5) for anonymous access"""
    demo_files = []
    for file_id in [1, 2, 3, 4, 5]:
        file_record = await repo_get_file_by_id(db, file_id)
        if file_record:
            demo_files.append(file_record)
    return demo_files


async def get_file_data_as_base64(file_record: models.FileStorage) -> Optional[str]:
    """Get file data as base64 encoded string"""
    try:
        file_path = await get_file_download_path(file_record)
        if not file_path or not file_path.exists():
            return None
        
        import base64
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            base64_data = base64.b64encode(file_bytes).decode('utf-8')
            return base64_data
            
    except Exception as e:
        logger.error(f"Error getting file data as base64: {e}")
        return None
