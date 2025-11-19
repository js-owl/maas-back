"""
Bitrix synchronization service
Handles queuing of Bitrix sync operations via Redis Streams
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.queue_service import bitrix_queue_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixSyncService:
    """Service for managing Bitrix synchronization via Redis Streams"""
    
    def __init__(self):
        self.max_attempts = 5
        self.retry_delays = [60, 300, 900, 3600, 14400]  # 1min, 5min, 15min, 1hr, 4hr
    
    async def queue_deal_creation(
        self, 
        db: AsyncSession, 
        order_id: int, 
        user_id: int, 
        file_id: Optional[int] = None, 
        document_ids: Optional[list] = None
    ) -> None:
        """Queue order→deal sync operation to Redis Streams"""
        try:
            # Get order and user data
            order_result = await db.execute(select(models.Order).where(models.Order.order_id == order_id))
            order = order_result.scalar_one_or_none()
            
            user_result = await db.execute(select(models.User).where(models.User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not order or not user:
                logger.error(f"[QUEUE_DEAL] Order {order_id} or User {user_id} not found")
                return
            
            # Prepare payload
            payload = {
                "order_id": order_id,
                "user_id": user_id,
                "file_id": file_id,
                "document_ids": document_ids or [],
                "order_data": {
                    "service_id": order.service_id,
                    "quantity": order.quantity,
                    "total_price": order.total_price,
                    "status": order.status,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                },
                "user_data": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type
                }
            }
            
            # Publish to Redis Stream
            message_id = await bitrix_queue_service.publish_operation(
                entity_type="deal",
                entity_id=order_id,
                operation="create",
                payload=payload
            )
            
            if message_id:
                logger.info(f"[QUEUE_DEAL] Queued deal creation for order {order_id} (message_id: {message_id})")
            else:
                logger.error(f"[QUEUE_DEAL] Failed to queue deal creation for order {order_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_DEAL] Error queuing deal creation: {e}", exc_info=True)
            raise
    
    async def queue_deal_update(
        self,
        db: AsyncSession,
        order_id: int
    ) -> None:
        """Queue order→deal update operation to Redis Streams"""
        try:
            # Get order data
            order_result = await db.execute(select(models.Order).where(models.Order.order_id == order_id))
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.error(f"[QUEUE_DEAL_UPDATE] Order {order_id} not found")
                return
            
            # Check if deal exists
            if not order.bitrix_deal_id:
                logger.warning(f"[QUEUE_DEAL_UPDATE] Order {order_id} has no Bitrix deal ID, skipping update")
                return
            
            # Prepare payload
            payload = {
                "order_id": order_id,
                "bitrix_deal_id": order.bitrix_deal_id,
                "order_data": {
                    "service_id": order.service_id,
                    "quantity": order.quantity,
                    "total_price": order.total_price,
                    "status": order.status,
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None
                }
            }
            
            # Publish to Redis Stream
            message_id = await bitrix_queue_service.publish_operation(
                entity_type="deal",
                entity_id=order_id,
                operation="update",
                payload=payload
            )
            
            if message_id:
                logger.info(f"[QUEUE_DEAL_UPDATE] Queued deal update for order {order_id} (message_id: {message_id})")
            else:
                logger.error(f"[QUEUE_DEAL_UPDATE] Failed to queue deal update for order {order_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_DEAL_UPDATE] Error queuing deal update: {e}", exc_info=True)
            raise
    
    async def queue_contact_creation(self, db: AsyncSession, user_id: int) -> None:
        """Queue user→contact sync operation to Redis Streams"""
        try:
            # Get user data
            user_result = await db.execute(select(models.User).where(models.User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"[QUEUE_CONTACT] User {user_id} not found")
                return
            
            # Check if already synced
            if user.bitrix_contact_id:
                logger.info(f"[QUEUE_CONTACT] User {user_id} already has Bitrix contact {user.bitrix_contact_id}")
                return
            
            # Prepare payload
            payload = {
                "user_id": user_id,
                "user_data": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type,
                    "company": user.company,
                    "city": user.city
                }
            }
            
            # Publish to Redis Stream
            message_id = await bitrix_queue_service.publish_operation(
                entity_type="contact",
                entity_id=user_id,
                operation="create",
                payload=payload
            )
            
            if message_id:
                logger.info(f"[QUEUE_CONTACT] Queued contact creation for user {user_id} (message_id: {message_id})")
            else:
                logger.error(f"[QUEUE_CONTACT] Failed to queue contact creation for user {user_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_CONTACT] Error queuing contact creation: {e}", exc_info=True)
            raise
    
    async def queue_lead_creation(self, db: AsyncSession, call_request_id: int) -> None:
        """Queue call_request→lead sync operation to Redis Streams"""
        try:
            # Get call request data
            cr_result = await db.execute(select(models.CallRequest).where(models.CallRequest.id == call_request_id))
            call_request = cr_result.scalar_one_or_none()
            
            if not call_request:
                logger.error(f"[QUEUE_LEAD] Call request {call_request_id} not found")
                return
            
            # Get user data
            user_result = await db.execute(select(models.User).where(models.User.id == call_request.user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"[QUEUE_LEAD] User {call_request.user_id} not found for call request {call_request_id}")
                return
            
            # Prepare payload
            payload = {
                "call_request_id": call_request_id,
                "user_id": call_request.user_id,
                "call_request_data": {
                    "name": call_request.name,
                    "phone": call_request.phone,
                    "email": call_request.email,
                    "date": call_request.date,
                    "time": call_request.time,
                    "additional": call_request.additional,
                    "status": call_request.status,
                    "created_at": call_request.created_at.isoformat() if call_request.created_at else None
                },
                "user_data": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type
                }
            }
            
            # Publish to Redis Stream
            message_id = await bitrix_queue_service.publish_operation(
                entity_type="lead",
                entity_id=call_request_id,
                operation="create",
                payload=payload
            )
            
            if message_id:
                logger.info(f"[QUEUE_LEAD] Queued lead creation for call request {call_request_id} (message_id: {message_id})")
            else:
                logger.error(f"[QUEUE_LEAD] Failed to queue lead creation for call request {call_request_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_LEAD] Error queuing lead creation: {e}", exc_info=True)
            raise
    
    # Note: process_sync_queue() and _process_*_sync() methods removed
    # Processing is now handled by the BitrixWorker consuming from Redis Streams
    
    async def get_sync_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get sync queue status from Redis Streams"""
        try:
            # Get stream information
            operations_info = await bitrix_queue_service.get_stream_info(
                bitrix_queue_service.operations_stream
            )
            webhooks_info = await bitrix_queue_service.get_stream_info(
                bitrix_queue_service.webhooks_stream
            )
            
            return {
                "operations_stream": {
                    "length": operations_info.get("length", 0),
                    "groups": operations_info.get("groups", 0),
                    "last_id": operations_info.get("last_id", "0-0")
                },
                "webhooks_stream": {
                    "length": webhooks_info.get("length", 0),
                    "groups": webhooks_info.get("groups", 0),
                    "last_id": webhooks_info.get("last_id", "0-0")
                },
                "total_messages": operations_info.get("length", 0) + webhooks_info.get("length", 0),
                "bitrix_configured": bitrix_client.is_configured()
            }
            
        except Exception as e:
            logger.error(f"[SYNC_STATUS] Error getting sync status: {e}", exc_info=True)
            return {
                "operations_stream": {"length": 0, "groups": 0, "last_id": "0-0"},
                "webhooks_stream": {"length": 0, "groups": 0, "last_id": "0-0"},
                "total_messages": 0,
                "bitrix_configured": bitrix_client.is_configured(),
                "error": str(e)
            }


# Global instance
bitrix_sync_service = BitrixSyncService()
