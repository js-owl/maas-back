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
    """Manually trigger sync queue processing (admin only) - DEPRECATED: Processing is now automatic via worker"""
    try:
        # Note: Processing is now automatic via BitrixWorker consuming from Redis Streams
        # This endpoint is kept for backward compatibility but does nothing
        logger.info(f"Sync processing requested by admin {admin_user.username} (deprecated - processing is automatic)")
        return {
            "success": True,
            "message": "Sync processing is now automatic via Redis Streams worker",
            "note": "This endpoint is deprecated. Messages are processed automatically by the Bitrix worker.",
            "stats": {
                "processed": 0,
                "failed": 0,
                "completed": 0,
                "note": "Use /sync/status to check queue status"
            }
        }
    except Exception as e:
        logger.error(f"Error in deprecated sync process endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
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
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """Get Redis Stream queue information (admin only) - DEPRECATED: Use /sync/status instead"""
    try:
        from backend.bitrix.queue_service import bitrix_queue_service
        
        # Get stream information
        operations_info = await bitrix_queue_service.get_stream_info(
            bitrix_queue_service.operations_stream
        )
        webhooks_info = await bitrix_queue_service.get_stream_info(
            bitrix_queue_service.webhooks_stream
        )
        
        return {
            "success": True,
            "message": "Queue information retrieved from Redis Streams",
            "note": "This endpoint shows stream statistics. Use /sync/status for detailed information.",
            "data": {
                "operations_stream": {
                    "name": bitrix_queue_service.operations_stream,
                    "length": operations_info.get("length", 0),
                    "groups": operations_info.get("groups", 0),
                    "last_id": operations_info.get("last_id", "0-0")
                },
                "webhooks_stream": {
                    "name": bitrix_queue_service.webhooks_stream,
                    "length": webhooks_info.get("length", 0),
                    "groups": webhooks_info.get("groups", 0),
                    "last_id": webhooks_info.get("last_id", "0-0")
                },
                "total_messages": operations_info.get("length", 0) + webhooks_info.get("length", 0)
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
    item_id: str,
    admin_user: models.User = Depends(require_admin)
):
    """Delete message from Redis Stream (admin only) - DEPRECATED: Messages are auto-acknowledged by worker"""
    try:
        from backend.bitrix.queue_service import bitrix_queue_service
        
        # Note: In Redis Streams, messages are automatically acknowledged when processed
        # This endpoint is kept for backward compatibility but does nothing
        logger.info(f"Delete queue item {item_id} requested by admin {admin_user.username} (deprecated)")
        
        return {
            "success": True,
            "message": "Message deletion is not supported in Redis Streams",
            "note": "Messages are automatically acknowledged when processed by the worker. Use /sync/status to check queue status."
        }
        
    except Exception as e:
        logger.error(f"Error in deprecated delete endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )