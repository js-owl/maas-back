"""
Invoices router
Handles invoice retrieval and download endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user
from backend.invoices.service import (
    get_invoice_by_id,
    get_invoices_by_order_id,
    get_invoice_download_path
)
from backend.orders.service import get_order_by_id
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/invoices/order/{order_id}', tags=["Invoices"])
async def invoices_order_options():
    """Handle CORS preflight requests for order invoices"""
    return Response(status_code=200)

@router.options('/invoices/{invoice_id}', tags=["Invoices"])
async def invoice_options():
    """Handle CORS preflight requests for invoice by ID"""
    return Response(status_code=200)

@router.options('/invoices/{invoice_id}/download', tags=["Invoices"])
async def invoice_download_options():
    """Handle CORS preflight requests for invoice download"""
    return Response(status_code=200)

@router.options('/orders/{order_id}/invoices/refresh', tags=["Invoices"])
async def invoice_refresh_options():
    """Handle CORS preflight requests for invoice refresh"""
    return Response(status_code=200)


@router.get('/invoices/order/{order_id}', response_model=List[schemas.InvoiceOut], tags=["Invoices"])
async def get_order_invoices(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all invoices for an order"""
    try:
        # Get order to check permissions
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get invoices for the order
        invoices = await get_invoices_by_order_id(db, order_id)
        
        return invoices
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoices for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get order invoices")


@router.get('/invoices/{invoice_id}', response_model=schemas.InvoiceOut, tags=["Invoices"])
async def get_invoice(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice information by ID"""
    try:
        invoice_record = await get_invoice_by_id(db, invoice_id)
        if not invoice_record:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get order to check permissions
        order = await get_order_by_id(db, invoice_record.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions (user must own the order or be admin)
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return invoice_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get invoice")


@router.get('/invoices/{invoice_id}/download', tags=["Invoices"])
async def download_invoice(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download invoice file by ID"""
    try:
        invoice_record = await get_invoice_by_id(db, invoice_id)
        if not invoice_record:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get order to check permissions
        order = await get_order_by_id(db, invoice_record.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get invoice path
        invoice_path = await get_invoice_download_path(invoice_record)
        if not invoice_path or not invoice_path.exists():
            raise HTTPException(status_code=404, detail="Invoice file not found on disk")
        
        # Return invoice file
        return FileResponse(
            path=str(invoice_path),
            filename=invoice_record.original_filename,
            media_type='application/pdf' if invoice_record.file_type == 'pdf' else 'application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.post('/orders/{order_id}/invoices/refresh', tags=["Invoices"])
async def refresh_order_invoice(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually check Bitrix for new invoice and download it"""
    try:
        # Get order to check permissions
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Use deal sync service to check and download invoice
        from backend.bitrix.deal_sync_service import BitrixDealSyncService
        sync_service = BitrixDealSyncService()
        
        if not order.bitrix_deal_id:
            raise HTTPException(status_code=400, detail="Order has no Bitrix deal ID")
        
        success = await sync_service.check_and_download_invoice(db, order_id, order.bitrix_deal_id)
        
        if success:
            return {
                "success": True,
                "message": "Invoice refreshed successfully"
            }
        else:
            return {
                "success": False,
                "message": "No new invoice found or failed to download"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing invoice for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh invoice")

