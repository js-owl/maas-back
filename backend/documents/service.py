"""
Documents service module
Business logic for document upload, download, and management
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from backend import models, schemas
from backend.documents.repository import (
    create_document as repo_create_document,
    get_document_by_id as repo_get_document_by_id,
    get_documents_by_ids as repo_get_documents_by_ids,
    get_documents_by_user as repo_get_documents_by_user,
    get_documents_by_category as repo_get_documents_by_category,
    delete_document as repo_delete_document
)
from backend.documents.storage import document_storage
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def upload_document_from_base64(
    db: AsyncSession, 
    document_name: str, 
    document_data: str, 
    user_id: int, 
    category: str = None
) -> models.DocumentStorage:
    """Upload document from base64 encoded data"""
    try:
        # Save document to storage
        document_metadata = await document_storage.save_document_from_base64(
            document_name, document_data, user_id, category
        )
        
        # Create database record
        db_document = await repo_create_document(db, document_metadata)
        
        logger.info(f"Document uploaded successfully: {document_name} (ID: {db_document.id})")
        return db_document
        
    except Exception as e:
        logger.error(f"Error uploading document {document_name}: {e}")
        raise




async def get_document_by_id(db: AsyncSession, document_id: int) -> Optional[models.DocumentStorage]:
    """Get document by ID"""
    return await repo_get_document_by_id(db, document_id)


async def get_documents_by_ids(db: AsyncSession, document_ids: List[int]) -> List[models.DocumentStorage]:
    """Get multiple documents by their IDs"""
    return await repo_get_documents_by_ids(db, document_ids)


async def get_documents_by_user(db: AsyncSession, user_id: int) -> List[models.DocumentStorage]:
    """Get all documents uploaded by a user"""
    return await repo_get_documents_by_user(db, user_id)


async def get_documents_by_category(db: AsyncSession, category: str) -> List[models.DocumentStorage]:
    """Get all documents by category"""
    return await repo_get_documents_by_category(db, category)


async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete document and its storage"""
    document_record = await repo_get_document_by_id(db, document_id)
    if not document_record:
        return False
    
    # Delete from storage
    if document_record.document_name:
        document_storage.delete_document(document_record.document_name)
    
    # Delete database record
    return await repo_delete_document(db, document_id)


async def get_document_download_path(document_record: models.DocumentStorage) -> Optional[Path]:
    """Get document path for download"""
    if not document_record or not document_record.document_path:
        return None
    
    document_path = Path(document_record.document_path)
    if document_path.exists():
        return document_path
    
    return None


def get_supported_formats() -> List[str]:
    """Get list of supported document formats"""
    return document_storage.get_supported_formats()


async def create_document_from_file_path(
    db: AsyncSession,
    file_path: str,
    user_id: int,
    category: str = None,
    original_filename: str = None
) -> Optional[models.DocumentStorage]:
    """Create document record from existing file path"""
    try:
        from datetime import datetime, timezone
        import os
        
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File does not exist: {file_path}")
            return None
        
        # Get file metadata
        file_size = path.stat().st_size
        file_extension = path.suffix.lower()
        
        # Determine file type from extension
        file_type = file_extension[1:] if file_extension else "unknown"
        
        # Use provided original filename or derive from path
        if not original_filename:
            original_filename = path.name
        
        # Generate unique filename if needed (to avoid conflicts)
        # For now, use the existing filename since the file already exists
        unique_filename = path.name
        
        # Prepare document data
        document_data = {
            "filename": unique_filename,
            "original_filename": original_filename,
            "file_path": str(path),
            "file_size": file_size,
            "file_type": file_type,
            "uploaded_by": user_id,
            "document_category": category,
            "uploaded_at": datetime.now(timezone.utc)
        }
        
        # Create database record
        db_document = await repo_create_document(db, document_data)
        
        logger.info(f"Document created from file path: {file_path} (ID: {db_document.id})")
        return db_document
        
    except Exception as e:
        logger.error(f"Error creating document from file path {file_path}: {e}", exc_info=True)
        return None