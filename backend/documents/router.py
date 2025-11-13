"""
Documents router
Handles document upload, download, and management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pathlib import Path
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend.documents.service import (
    upload_document_from_base64,
    get_document_by_id,
    get_documents_by_user,
    get_documents_by_category,
    delete_document,
    get_document_download_path,
    get_supported_formats
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/documents', tags=["Documents"])
async def documents_options():
    """Handle CORS preflight requests for documents"""
    return Response(status_code=200)

@router.options('/documents/{document_id}', tags=["Documents"])
async def document_options():
    """Handle CORS preflight requests for document by ID"""
    return Response(status_code=200)

@router.options('/documents/{document_id}/download', tags=["Documents"])
async def document_download_options():
    """Handle CORS preflight requests for document download"""
    return Response(status_code=200)

# CORS preflight handler for document upload
@router.post('/documents', response_model=schemas.DocumentUploadResponse, tags=["Documents"])
async def upload_document(
    request_data: schemas.DocumentUploadRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document file using JSON with base64 data"""
    try:
        # Upload document from base64
        db_document = await upload_document_from_base64(
            db, 
            request_data.document_name, 
            request_data.document_data, 
            current_user.id, 
            request_data.document_category
        )
        
        return {
            "document_id": db_document.id,
            "filename": db_document.filename,
            "original_filename": db_document.original_filename,
            "file_size": db_document.file_size,
            "file_type": db_document.file_type,
            "document_category": db_document.document_category
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document from JSON: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {e.__traceback__}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@router.get('/documents/formats', response_model=List[str], tags=["Documents"])
async def get_document_formats():
    """Get list of supported document formats"""
    try:
        formats = get_supported_formats()
        return formats
    except Exception as e:
        logger.error(f"Error getting document formats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document formats")


@router.get('/documents/{document_id}', response_model=schemas.DocumentStorageOut, tags=["Documents"])
async def get_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document information by ID"""
    try:
        document_record = await get_document_by_id(db, document_id)
        if not document_record:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check access permissions
        if document_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return document_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.get('/documents/{document_id}/download', tags=["Documents"])
async def download_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download document by ID"""
    try:
        document_record = await get_document_by_id(db, document_id)
        if not document_record:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check access permissions
        if document_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get document path
        document_path = await get_document_download_path(document_record)
        if not document_path or not document_path.exists():
            raise HTTPException(status_code=404, detail="Document not found on disk")
        
        # Return document
        return FileResponse(
            path=str(document_path),
            filename=document_record.original_filename or document_record.document_name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.get('/documents', response_model=List[schemas.DocumentStorageOut], tags=["Documents"])
async def list_documents(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents uploaded by current user"""
    try:
        documents = await get_documents_by_user(db, current_user.id)
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get('/documents/category/{category}', response_model=List[schemas.DocumentStorageOut], tags=["Documents"])
async def list_documents_by_category(
    category: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List documents by category"""
    try:
        documents = await get_documents_by_category(db, category)
        return documents
    except Exception as e:
        logger.error(f"Error listing documents by category {category}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get('/users/{user_id}/documents', response_model=List[schemas.DocumentStorageOut], tags=["Admin", "Documents"])
async def list_user_documents(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List documents uploaded by a specific user (admin only)"""
    try:
        # Only admins can list other users' documents
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        documents = await get_documents_by_user(db, user_id)
        return documents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.delete('/documents/{document_id}', response_model=schemas.MessageResponse, tags=["Documents"])
async def delete_document_endpoint(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete document (owner or admin only)"""
    try:
        document_record = await get_document_by_id(db, document_id)
        if not document_record:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check access permissions
        if document_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = await delete_document(db, document_id)
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Document deletion failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Document deletion failed")
