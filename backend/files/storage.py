"""
Files storage module
File system operations for file uploads and management
"""
import os
import uuid
import shutil
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import HTTPException
import logging

# For future S3 implementation
# import boto3
# from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class FileStorageService:
    """File storage service supporting local disk storage with S3 commented for future use"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.getenv("UPLOAD_DIR", "uploads/3d_models")
        
        self.base_path = Path(base_path)
        self.models_path = self.base_path
        self.temp_path = Path(os.getenv("TEMP_DIR", "uploads/temp"))
        
        # Ensure directories exist
        self.models_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # S3 configuration for future use
        # self.s3_client = None
        # self.s3_bucket = "your-bucket-name"
        # self.use_s3 = False  # Set to True to use S3 instead of local storage
    
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
    
    
    async def save_file_from_base64(self, file_name: str, file_data: str, user_id: int) -> Dict[str, Any]:
        """Save file from base64 encoded data"""
        try:
            import base64
            
            # Decode base64 data
            file_bytes = base64.b64decode(file_data)
            
            # Generate unique filename
            unique_filename = self._generate_unique_filename(file_name)
            file_path = self.models_path / unique_filename
            
            # Save file to disk
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)
            
            # Get file metadata
            metadata = self._get_file_metadata(file_path)
            
            # Prepare file data for database
            file_extension = Path(file_name).suffix.lower()
            file_data = {
                "filename": unique_filename,
                "original_filename": file_name,
                "file_path": str(file_path),
                "file_size": metadata["file_size"],
                "file_type": file_extension,
                "uploaded_by": user_id,
                "uploaded_at": datetime.now(timezone.utc),
                "is_demo": False  # Regular uploads are not demo files
            }
            
            logger.info(f"File saved from base64: {unique_filename} (size: {metadata['file_size']} bytes)")
            return file_data
            
        except Exception as e:
            logger.error(f"Error saving file from base64 {file_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    def get_file_path(self, filename: str) -> Path:
        """Get full file path for a filename"""
        return self.models_path / filename
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in storage"""
        return self.get_file_path(filename).exists()
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from storage"""
        try:
            file_path = self.get_file_path(filename)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False
    
    def get_file_size(self, filename: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            file_path = self.get_file_path(filename)
            if file_path.exists():
                return file_path.stat().st_size
            return None
        except Exception as e:
            logger.error(f"Error getting file size for {filename}: {e}")
            return None


# Global instance
file_storage = FileStorageService()
