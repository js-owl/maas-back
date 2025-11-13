"""
Documents storage module
Document file system operations
"""
import os
import uuid
import shutil
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentStorageService:
    """Document storage service for additional documents like drawings, specifications, etc."""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.getenv("DOCUMENTS_DIR", "uploads/documents")
        
        self.base_path = Path(base_path)
        self.documents_path = self.base_path
        self.temp_path = Path(os.getenv("TEMP_DIR", "uploads/temp"))
        
        # Ensure directories exist
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Supported document types
        self.allowed_extensions = {
            # Drawings and technical documents
            '.dwg', '.dxf', '.pdf', '.svg', '.ai', '.eps',
            # Office documents
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            # Text and markup
            '.txt', '.rtf', '.md', '.html', '.xml',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            # CAD and 3D (including STL for supplemental 3D models)
            '.step', '.stp', '.iges', '.igs', '.sat', '.sldprt', '.sldasm',
            '.stl', '.obj', '.ply', '.3ds', '.dae', '.fbx', '.blend',
            # Archives
            '.zip', '.rar', '.7z', '.tar', '.gz'
        }
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename to prevent conflicts"""
        file_extension = Path(original_filename).suffix
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"
    
    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file metadata"""
        stat = file_path.stat()
        return {
            "file_size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    
    def _validate_file_type(self, filename: str) -> bool:
        """Validate if file type is allowed"""
        file_extension = Path(filename).suffix.lower()
        return file_extension in self.allowed_extensions
    
    
    async def save_document_from_base64(self, document_name: str, document_data: str, user_id: int, category: str = None) -> Dict[str, Any]:
        """Save document from base64 encoded data"""
        try:
            import base64
            
            # Validate file type
            if not self._validate_file_type(document_name):
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type not allowed. Allowed types: {', '.join(sorted(self.allowed_extensions))}"
                )
            
            # Decode base64 data
            file_bytes = base64.b64decode(document_data)
            
            # Generate unique filename
            unique_filename = self._generate_unique_filename(document_name)
            file_path = self.documents_path / unique_filename
            
            # Save file to disk
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)
            
            # Get file metadata
            metadata = self._get_file_metadata(file_path)
            
            # Prepare document data for database
            document_data = {
                "filename": unique_filename,
                "original_filename": document_name,
                "file_path": str(file_path),
                "file_size": metadata["file_size"],
                "file_type": metadata.get("file_type", ""),
                "uploaded_by": user_id,
                "document_category": category,
                "uploaded_at": datetime.now(timezone.utc)
            }
            
            logger.info(f"Document saved from base64: {unique_filename} (size: {metadata['file_size']} bytes)")
            return document_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving document from base64 {document_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")
    
    def get_document_path(self, document_name: str) -> Path:
        """Get full document path for a document name"""
        return self.documents_path / document_name
    
    def document_exists(self, document_name: str) -> bool:
        """Check if document exists in storage"""
        return self.get_document_path(document_name).exists()
    
    def delete_document(self, document_name: str) -> bool:
        """Delete document from storage"""
        try:
            document_path = self.get_document_path(document_name)
            if document_path.exists():
                document_path.unlink()
                logger.info(f"Document deleted: {document_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting document {document_name}: {e}")
            return False
    
    def get_document_size(self, document_name: str) -> Optional[int]:
        """Get document size in bytes"""
        try:
            document_path = self.get_document_path(document_name)
            if document_path.exists():
                return document_path.stat().st_size
            return None
        except Exception as e:
            logger.error(f"Error getting document size for {document_name}: {e}")
            return None
    
    def get_supported_formats(self) -> list:
        """Get list of supported document formats"""
        return sorted(list(self.allowed_extensions))


# Global instance
document_storage = DocumentStorageService()
