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
            
            # Check if already synced
            if order.bitrix_deal_id:
                logger.info(f"[QUEUE_DEAL] Order {order_id} already has Bitrix deal {order.bitrix_deal_id}")
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
    
    async def queue_contact_update(self, db: AsyncSession, user_id: int) -> None:
        """Queue user→contact update operation to Redis Streams"""
        try:
            # Get user data
            user_result = await db.execute(select(models.User).where(models.User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"[QUEUE_CONTACT_UPDATE] User {user_id} not found")
                return
            
            # Check if contact exists
            if not user.bitrix_contact_id:
                logger.warning(f"[QUEUE_CONTACT_UPDATE] User {user_id} has no Bitrix contact ID, skipping update")
                return
            
            # Prepare payload
            payload = {
                "user_id": user_id,
                "bitrix_contact_id": user.bitrix_contact_id,
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
                operation="update",
                payload=payload
            )
            
            if message_id:
                logger.info(f"[QUEUE_CONTACT_UPDATE] Queued contact update for user {user_id} (contact_id: {user.bitrix_contact_id}, message_id: {message_id})")
            else:
                logger.error(f"[QUEUE_CONTACT_UPDATE] Failed to queue contact update for user {user_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_CONTACT_UPDATE] Error queuing contact update: {e}", exc_info=True)
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
    
    async def sync_all_orders_to_bitrix(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync all orders without Bitrix deals to Bitrix via Redis queue"""
        try:
            # Query all orders without bitrix_deal_id
            orders_result = await db.execute(
                select(models.Order)
                .where(models.Order.bitrix_deal_id.is_(None))
                .order_by(models.Order.order_id)
            )
            orders = orders_result.scalars().all()
            
            total_orders = len(orders)
            queued_count = 0
            skipped_count = 0
            error_count = 0
            
            logger.info(f"[SYNC_ALL_ORDERS] Found {total_orders} orders without Bitrix deals")
            
            for order in orders:
                try:
                    # Get user for the order
                    user_result = await db.execute(
                        select(models.User).where(models.User.id == order.user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        logger.warning(f"[SYNC_ALL_ORDERS] User {order.user_id} not found for order {order.order_id}, skipping")
                        skipped_count += 1
                        continue
                    
                    # Queue deal creation (this will check for duplicates again, but that's fine)
                    await self.queue_deal_creation(
                        db=db,
                        order_id=order.order_id,
                        user_id=order.user_id,
                        file_id=order.file_id,
                        document_ids=None  # Could parse from order.document_ids if needed
                    )
                    queued_count += 1
                    
                except Exception as e:
                    logger.error(f"[SYNC_ALL_ORDERS] Error queuing order {order.order_id}: {e}", exc_info=True)
                    error_count += 1
            
            result = {
                "total_orders": total_orders,
                "queued_count": queued_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "message": f"Queued {queued_count} orders for Bitrix sync"
            }
            
            logger.info(f"[SYNC_ALL_ORDERS] Completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[SYNC_ALL_ORDERS] Error syncing all orders: {e}", exc_info=True)
            raise
    
    async def sync_all_contacts_to_bitrix(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync all users without Bitrix contacts to Bitrix via Redis queue"""
        try:
            # Query all users without bitrix_contact_id
            users_result = await db.execute(
                select(models.User)
                .where(models.User.bitrix_contact_id.is_(None))
                .order_by(models.User.id)
            )
            users = users_result.scalars().all()
            
            total_users = len(users)
            queued_count = 0
            skipped_count = 0
            error_count = 0
            
            logger.info(f"[SYNC_ALL_CONTACTS] Found {total_users} users without Bitrix contacts")
            
            for user in users:
                try:
                    # Queue contact creation (this will check for duplicates again, but that's fine)
                    await self.queue_contact_creation(db=db, user_id=user.id)
                    queued_count += 1
                    
                except Exception as e:
                    logger.error(f"[SYNC_ALL_CONTACTS] Error queuing user {user.id}: {e}", exc_info=True)
                    error_count += 1
            
            result = {
                "total_users": total_users,
                "queued_count": queued_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "message": f"Queued {queued_count} contacts for Bitrix sync"
            }
            
            logger.info(f"[SYNC_ALL_CONTACTS] Completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[SYNC_ALL_CONTACTS] Error syncing all contacts: {e}", exc_info=True)
            raise
    
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
