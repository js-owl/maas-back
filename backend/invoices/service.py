"""
Invoices service module
Business logic for invoice management
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from backend import models
from backend.invoices.repository import (
    create_invoice as repo_create_invoice,
    get_invoice_by_id as repo_get_invoice_by_id,
    get_invoices_by_ids as repo_get_invoices_by_ids,
    get_invoices_by_order_id as repo_get_invoices_by_order_id,
    delete_invoice as repo_delete_invoice
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def get_invoice_by_id(db: AsyncSession, invoice_id: int) -> Optional[models.InvoiceStorage]:
    """Get invoice by ID"""
    return await repo_get_invoice_by_id(db, invoice_id)


async def get_invoices_by_ids(db: AsyncSession, invoice_ids: List[int]) -> List[models.InvoiceStorage]:
    """Get multiple invoices by their IDs"""
    return await repo_get_invoices_by_ids(db, invoice_ids)


async def get_invoices_by_order_id(db: AsyncSession, order_id: int) -> List[models.InvoiceStorage]:
    """Get all invoices for a specific order"""
    return await repo_get_invoices_by_order_id(db, order_id)


async def get_invoice_download_path(invoice_record: models.InvoiceStorage) -> Optional[Path]:
    """Get the file path for downloading an invoice"""
    if not invoice_record.file_path:
        return None
    
    path = Path(invoice_record.file_path)
    if path.exists():
        return path
    
    return None


async def create_invoice_from_file_path(
    db: AsyncSession,
    file_path: str,
    order_id: int,
    bitrix_document_id: Optional[int] = None,
    generated_at: Optional[datetime] = None,
    original_filename: Optional[str] = None
) -> Optional[models.InvoiceStorage]:
    """Create invoice record from existing file path"""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Invoice file does not exist: {file_path}")
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
        unique_filename = path.name
        
        # Prepare invoice data
        invoice_data = {
            "filename": unique_filename,
            "original_filename": original_filename,
            "file_path": str(path),
            "file_size": file_size,
            "file_type": file_type,
            "order_id": order_id,
            "bitrix_document_id": bitrix_document_id,
            "generated_at": generated_at or datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Create database record
        db_invoice = await repo_create_invoice(db, invoice_data)
        
        logger.info(f"Invoice created from file path: {file_path} (ID: {db_invoice.id})")
        return db_invoice
        
    except Exception as e:
        logger.error(f"Error creating invoice from file path {file_path}: {e}", exc_info=True)
        return None


async def delete_invoice(db: AsyncSession, invoice_id: int) -> bool:
    """Delete invoice record"""
    return await repo_delete_invoice(db, invoice_id)

