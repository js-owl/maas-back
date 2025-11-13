"""
Files router
Handles file upload, download, preview, and management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pathlib import Path
import io
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user, get_current_admin_user, get_optional_current_user
from backend.files.service import (
    upload_file_from_base64,
    get_file_by_id,
    get_files_by_user,
    delete_file,
    get_file_download_path,
    get_file_preview_path,
    regenerate_preview,
    get_demo_files
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/files', tags=["Files"])
async def files_options():
    """Handle CORS preflight requests for files"""
    return Response(status_code=200)

@router.options('/files/demo', tags=["Files"])
async def files_demo_options():
    """Handle CORS preflight requests for demo files"""
    return Response(status_code=200)

@router.options('/files/{file_id}', tags=["Files"])
async def file_options():
    """Handle CORS preflight requests for file by ID"""
    return Response(status_code=200)

@router.options('/files/{file_id}/download', tags=["Files"])
async def file_download_options():
    """Handle CORS preflight requests for file download"""
    return Response(status_code=200)

@router.options('/files/{file_id}/preview', tags=["Files"])
async def file_preview_options():
    """Handle CORS preflight requests for file preview"""
    return Response(status_code=200)

@router.post('/files', response_model=schemas.FileUploadResponse, tags=["Files"])
async def upload_file_json(
    request_data: schemas.FileUploadRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a 3D model file using JSON with base64 data"""
    try:
        # Validate file type
        allowed_extensions = {'.stl', '.obj', '.ply', '.3ds', '.dae', '.fbx', '.blend', '.stp', '.step'}
        file_extension = Path(request_data.file_name).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="File type not allowed for upload")
        
        # Upload file from base64
        db_file = await upload_file_from_base64(
            db, 
            request_data.file_name, 
            request_data.file_data, 
            request_data.file_type,
            current_user.id, 
        )
        
        return {
            "id": db_file.id,
            "filename": db_file.original_filename or db_file.filename,
            "original_filename": db_file.original_filename or db_file.filename,
            "file_size": db_file.file_size,
            "file_type": db_file.file_type,
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file from JSON: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get('/files/demo', response_model=List[schemas.FileStorageOut], tags=["Files"])
async def get_demo_files_endpoint(db: AsyncSession = Depends(get_db)):
    """Get available demo 3D models for anonymous calculations"""
    try:
        demo_files = await get_demo_files(db)
        logger.info(f"Demo files requested: found {len(demo_files)} files")
        return demo_files
    except Exception as e:
        logger.error(f"Error getting demo files: {e}")
        raise HTTPException(status_code=500, detail="Failed to get demo files")


@router.get('/files/{file_id}', response_model=schemas.FileStorageOut, tags=["Files"])
async def get_file(
    file_id: int,
    current_user: Optional[models.User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file information by ID"""
    try:
        file_record = await get_file_by_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check access permissions
        is_demo = file_record.id in [1, 2, 3, 4, 5] or getattr(file_record, 'is_demo', False)
        
        # Allow access to demo files without authentication
        if is_demo:
            return file_record
        
        # For non-demo files, require authentication
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if file_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return file_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file")


@router.get('/files/{file_id}/download', tags=["Files"])
async def download_file(
    file_id: int,
    current_user: Optional[models.User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download file by ID"""
    try:
        file_record = await get_file_by_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check access permissions
        is_demo = file_record.id in [1, 2, 3, 4, 5] or getattr(file_record, 'is_demo', False)
        
        # Allow access to demo files without authentication
        if is_demo:
            # Get file path
            file_path = await get_file_download_path(file_record)
            if not file_path or not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found on disk")
            
            # Return file
            return FileResponse(
                path=str(file_path),
                filename=file_record.original_filename or file_record.filename,
                media_type='application/octet-stream'
            )
        
        # For non-demo files, require authentication
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if file_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get file path
        file_path = await get_file_download_path(file_record)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=file_record.original_filename or file_record.filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.get('/files/{file_id}/preview', tags=["Files", "Preview"])
async def get_file_preview(
    file_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file preview image"""
    try:
        file_record = await get_file_by_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check access permissions
        is_demo = file_record.id in [1, 2, 3, 4, 5] or getattr(file_record, 'is_demo', False)
        if not is_demo and file_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get preview path
        preview_path = await get_file_preview_path(db, file_id)
        if not preview_path or not preview_path.exists():
            # Return placeholder if no preview available
            from backend.utils.helpers import generate_placeholder_preview
            placeholder_data = generate_placeholder_preview(file_record.original_filename or file_record.filename)
            return StreamingResponse(
                io.BytesIO(placeholder_data),
                media_type="image/png",
                headers={"Content-Disposition": "inline"}
            )
        
        # Return preview image
        return FileResponse(
            path=str(preview_path),
            media_type="image/png",
            headers={"Content-Disposition": "inline"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Preview generation failed")

@router.delete('/files/{file_id}', response_model=schemas.MessageResponse, tags=["Files"])
async def delete_file_endpoint(
    file_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete file by ID"""
    try:
        # Get file from database
        file_record = await get_file_by_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user has access to this file
        if file_record.uploaded_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file using service
        success = await delete_file(db, file_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
        logger.info(f"File {file_id} deleted by user {current_user.id}")
        return schemas.MessageResponse(message="File deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@router.get('/files', response_model=List[schemas.FileStorageOut], tags=["Files"])
async def list_files(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all files uploaded by current user"""
    try:
        files = await get_files_by_user(db, current_user.id)
        return files
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")


@router.get('/users/{user_id}/files', response_model=List[schemas.FileStorageOut], tags=["Files"])
async def list_user_files(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List files uploaded by a specific user (admin only)"""
    try:
        # Only admins can list other users' files
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        files = await get_files_by_user(db, user_id)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")


@router.post('/admin/files/{file_id}/regenerate-preview', response_model=schemas.MessageResponse, tags=["Admin", "Preview"])
async def regenerate_file_preview(
    file_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate preview for a file (admin only)"""
    try:
        success = await regenerate_preview(db, file_id)
        if success:
            return {"message": "Preview regenerated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Preview regeneration failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating preview for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Preview regeneration failed")
