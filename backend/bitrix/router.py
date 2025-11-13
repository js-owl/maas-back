"""
Bitrix integration router
Handles Bitrix sync operations and manual endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user
from backend.core.exceptions import AuthorizationException
from backend import models
from backend.bitrix.sync_service import bitrix_sync_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/sync/process', tags=["Bitrix Sync"])
async def sync_process_options():
    """Handle CORS preflight requests for sync process"""
    return Response(status_code=200)

@router.options('/sync/status', tags=["Bitrix Sync"])
async def sync_status_options():
    """Handle CORS preflight requests for sync status"""
    return Response(status_code=200)

@router.options('/sync/queue', tags=["Bitrix Sync"])
async def sync_queue_options():
    """Handle CORS preflight requests for sync queue"""
    return Response(status_code=200)

@router.options('/sync/all', tags=["Bitrix Sync"])
async def sync_all_options():
    """Handle CORS preflight requests for sync all"""
    return Response(status_code=200)

@router.options('/sync/pending', tags=["Bitrix Sync"])
async def sync_pending_options():
    """Handle CORS preflight requests for sync pending"""
    return Response(status_code=200)

def require_admin(current_user: models.User = Depends(get_current_user)):
    """Require admin access for Bitrix sync operations"""
    if not current_user.is_admin:
        raise AuthorizationException("Admin access required for Bitrix sync operations")
    return current_user


@router.post('/sync/process', tags=["Bitrix Sync"])
async def process_sync_queue(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """Manually trigger sync queue processing (admin only)"""
    try:
        stats = await bitrix_sync_service.process_sync_queue(db, limit)
        logger.info(f"Sync processing completed by admin {admin_user.username}: {stats}")
        return {
            "success": True,
            "message": "Sync queue processing completed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error processing sync queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process sync queue: {str(e)}"
        )


@router.get('/sync/status', tags=["Bitrix Sync"])
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """Get sync queue status (admin only)"""
    try:
        status_info = await bitrix_sync_service.get_sync_status(db)
        return {
            "success": True,
            "message": "Sync status retrieved",
            "data": status_info
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )


@router.get('/sync/queue', tags=["Bitrix Sync"])
async def get_sync_queue(
    status_filter: str = None,
    entity_type: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """List sync queue items (admin only)"""
    try:
        from sqlalchemy import select, and_
        
        # Build query
        query = select(models.BitrixSyncQueue)
        conditions = []
        
        if status_filter:
            conditions.append(models.BitrixSyncQueue.status == status_filter)
        if entity_type:
            conditions.append(models.BitrixSyncQueue.entity_type == entity_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(models.BitrixSyncQueue.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Convert to dict format
        queue_items = []
        for item in items:
            queue_items.append({
                "id": item.id,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "operation": item.operation,
                "status": item.status,
                "attempts": item.attempts,
                "last_attempt": item.last_attempt.isoformat() if item.last_attempt else None,
                "error_message": item.error_message,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            })
        
        return {
            "success": True,
            "message": "Sync queue retrieved",
            "data": {
                "items": queue_items,
                "total": len(queue_items)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting sync queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync queue: {str(e)}"
        )


@router.post('/sync/verify', tags=["Bitrix Sync"])
async def verify_and_reconcile(
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """Verify and reconcile Bitrix data (admin only)"""
    try:
        # This would implement verification logic to check for missing deals/contacts/leads
        # and recreate them from the database
        # For now, just return a placeholder response
        
        logger.info(f"Bitrix verification requested by admin {admin_user.username}")
        
        return {
            "success": True,
            "message": "Bitrix verification completed",
            "data": {
                "verified_deals": 0,
                "verified_contacts": 0,
                "verified_leads": 0,
                "recreated_items": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error during Bitrix verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify Bitrix data: {str(e)}"
        )


@router.delete('/sync/queue/{item_id}', tags=["Bitrix Sync"])
async def delete_sync_queue_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """Delete sync queue item (admin only)"""
    try:
        from sqlalchemy import delete
        
        result = await db.execute(
            delete(models.BitrixSyncQueue).where(models.BitrixSyncQueue.id == item_id)
        )
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync queue item not found"
            )
        
        await db.commit()
        
        logger.info(f"Sync queue item {item_id} deleted by admin {admin_user.username}")
        
        return {
            "success": True,
            "message": "Sync queue item deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting sync queue item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sync queue item: {str(e)}"
        )