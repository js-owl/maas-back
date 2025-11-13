"""
Bitrix synchronization service
Handles queuing and processing of Bitrix sync operations
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend import models
from backend.core.exceptions import BitrixException, ExternalServiceException
from backend.bitrix.client import bitrix_client
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixSyncService:
    """Service for managing Bitrix synchronization queue"""
    
    def __init__(self):
        self.max_attempts = 5
        self.retry_delays = [60, 300, 900, 3600, 14400]  # 1min, 5min, 15min, 1hr, 4hr
    
    async def queue_deal_creation(
        self, 
        db: AsyncSession, 
        order_id: int, 
        user_id: int, 
        file_id: Optional[int] = None, 
        document_ids: Optional[List[int]] = None
    ) -> None:
        """Queue order→deal sync operation"""
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
            
            # Create sync queue entry
            sync_entry = models.BitrixSyncQueue(
                entity_type="deal",
                entity_id=order_id,
                operation="create",
                payload=json.dumps(payload),
                status="pending"
            )
            
            db.add(sync_entry)
            await db.commit()
            
            logger.info(f"[QUEUE_DEAL] Queued deal creation for order {order_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_DEAL] Error queuing deal creation: {e}")
            raise
    
    async def queue_contact_creation(self, db: AsyncSession, user_id: int) -> None:
        """Queue user→contact sync operation"""
        try:
            # Get user data
            user_result = await db.execute(select(models.User).where(models.User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"[QUEUE_CONTACT] User {user_id} not found")
                return
            
            # Check if already queued or synced
            existing_result = await db.execute(
                select(models.BitrixSyncQueue).where(
                    models.BitrixSyncQueue.entity_type == "contact",
                    models.BitrixSyncQueue.entity_id == user_id,
                    models.BitrixSyncQueue.status.in_(["pending", "processing", "completed"])
                )
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                logger.info(f"[QUEUE_CONTACT] Contact sync already queued for user {user_id}")
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
            
            # Create sync queue entry
            sync_entry = models.BitrixSyncQueue(
                entity_type="contact",
                entity_id=user_id,
                operation="create",
                payload=json.dumps(payload),
                status="pending"
            )
            
            db.add(sync_entry)
            await db.commit()
            
            logger.info(f"[QUEUE_CONTACT] Queued contact creation for user {user_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_CONTACT] Error queuing contact creation: {e}")
            raise
    
    async def queue_lead_creation(self, db: AsyncSession, call_request_id: int) -> None:
        """Queue call_request→lead sync operation"""
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
            
            # Create sync queue entry
            sync_entry = models.BitrixSyncQueue(
                entity_type="lead",
                entity_id=call_request_id,
                operation="create",
                payload=json.dumps(payload),
                status="pending"
            )
            
            db.add(sync_entry)
            await db.commit()
            
            logger.info(f"[QUEUE_LEAD] Queued lead creation for call request {call_request_id}")
            
        except Exception as e:
            logger.error(f"[QUEUE_LEAD] Error queuing lead creation: {e}")
            raise
    
    async def process_sync_queue(self, db: AsyncSession, limit: int = 10) -> Dict[str, int]:
        """Process pending sync queue items"""
        if not bitrix_client.is_configured():
            logger.warning("[PROCESS_SYNC] Bitrix not configured, skipping sync processing")
            return {"processed": 0, "failed": 0, "completed": 0}
        
        try:
            # Get pending items
            result = await db.execute(
                select(models.BitrixSyncQueue)
                .where(models.BitrixSyncQueue.status == "pending")
                .limit(limit)
            )
            pending_items = result.scalars().all()
            
            stats = {"processed": 0, "failed": 0, "completed": 0}
            
            for item in pending_items:
                try:
                    # Mark as processing
                    await db.execute(
                        update(models.BitrixSyncQueue)
                        .where(models.BitrixSyncQueue.id == item.id)
                        .values(
                            status="processing",
                            attempts=item.attempts + 1,
                            last_attempt=datetime.now(timezone.utc)
                        )
                    )
                    await db.commit()
                    
                    # Process based on entity type
                    success = False
                    if item.entity_type == "deal":
                        success = await self._process_deal_sync(db, item)
                    elif item.entity_type == "contact":
                        success = await self._process_contact_sync(db, item)
                    elif item.entity_type == "lead":
                        success = await self._process_lead_sync(db, item)
                    
                    if success:
                        # Mark as completed
                        await db.execute(
                            update(models.BitrixSyncQueue)
                            .where(models.BitrixSyncQueue.id == item.id)
                            .values(
                                status="completed",
                                error_message=None
                            )
                        )
                        stats["completed"] += 1
                        logger.info(f"[PROCESS_SYNC] Completed {item.entity_type} sync for entity {item.entity_id}")
                    else:
                        # Handle retry logic
                        if item.attempts >= self.max_attempts:
                            await db.execute(
                                update(models.BitrixSyncQueue)
                                .where(models.BitrixSyncQueue.id == item.id)
                                .values(status="failed")
                            )
                            stats["failed"] += 1
                            logger.error(f"[PROCESS_SYNC] Failed {item.entity_type} sync for entity {item.entity_id} after {item.attempts} attempts")
                        else:
                            await db.execute(
                                update(models.BitrixSyncQueue)
                                .where(models.BitrixSyncQueue.id == item.id)
                                .values(status="pending")
                            )
                            stats["failed"] += 1
                            logger.warning(f"[PROCESS_SYNC] Retrying {item.entity_type} sync for entity {item.entity_id} (attempt {item.attempts})")
                    
                    await db.commit()
                    stats["processed"] += 1
                    
                except Exception as e:
                    logger.error(f"[PROCESS_SYNC] Error processing sync item {item.id}: {e}")
                    stats["failed"] += 1
                    
                    # Mark as failed if max attempts reached
                    if item.attempts >= self.max_attempts:
                        await db.execute(
                            update(models.BitrixSyncQueue)
                            .where(models.BitrixSyncQueue.id == item.id)
                            .values(
                                status="failed",
                                error_message=str(e)
                            )
                        )
                    else:
                        await db.execute(
                            update(models.BitrixSyncQueue)
                            .where(models.BitrixSyncQueue.id == item.id)
                            .values(
                                status="pending",
                                error_message=str(e)
                            )
                        )
                    await db.commit()
            
            logger.info(f"[PROCESS_SYNC] Processed {stats['processed']} items: {stats['completed']} completed, {stats['failed']} failed")
            return stats
            
        except Exception as e:
            logger.error(f"[PROCESS_SYNC] Error processing sync queue: {e}")
            raise
    
    async def _process_deal_sync(self, db: AsyncSession, sync_item: models.BitrixSyncQueue) -> bool:
        """Process deal creation sync"""
        try:
            payload = json.loads(sync_item.payload)
            order_id = payload["order_id"]
            user_id = payload["user_id"]
            
            # Create deal in Bitrix
            deal_id = await bitrix_client.create_deal_from_order_data(
                order_data=payload["order_data"],
                user_data=payload["user_data"],
                file_id=payload.get("file_id"),
                document_ids=payload.get("document_ids", [])
            )
            
            if deal_id:
                # Update order with Bitrix deal ID
                await db.execute(
                    update(models.Order)
                    .where(models.Order.order_id == order_id)
                    .values(bitrix_deal_id=deal_id)
                )
                logger.info(f"[PROCESS_DEAL] Created Bitrix deal {deal_id} for order {order_id}")
                return True
            else:
                logger.error(f"[PROCESS_DEAL] Failed to create Bitrix deal for order {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"[PROCESS_DEAL] Error processing deal sync: {e}")
            return False
    
    async def _process_contact_sync(self, db: AsyncSession, sync_item: models.BitrixSyncQueue) -> bool:
        """Process contact creation sync"""
        try:
            payload = json.loads(sync_item.payload)
            user_id = payload["user_id"]
            
            # Create contact in Bitrix
            contact_id = await bitrix_client.create_contact(payload["user_data"])
            
            if contact_id:
                # Update user with Bitrix contact ID
                await db.execute(
                    update(models.User)
                    .where(models.User.id == user_id)
                    .values(bitrix_contact_id=contact_id)
                )
                logger.info(f"[PROCESS_CONTACT] Created Bitrix contact {contact_id} for user {user_id}")
                return True
            else:
                logger.error(f"[PROCESS_CONTACT] Failed to create Bitrix contact for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"[PROCESS_CONTACT] Error processing contact sync: {e}")
            return False
    
    async def _process_lead_sync(self, db: AsyncSession, sync_item: models.BitrixSyncQueue) -> bool:
        """Process lead creation sync"""
        try:
            payload = json.loads(sync_item.payload)
            call_request_id = payload["call_request_id"]
            user_id = payload["user_id"]
            
            # Create lead in Bitrix
            lead_id = await bitrix_client.create_lead(
                title=f"Call Request: {payload['call_request_data']['name']}",
                fields={
                    "NAME": payload["call_request_data"]["name"],
                    "PHONE": [{"VALUE": payload["call_request_data"]["phone"]}],
                    "EMAIL": [{"VALUE": payload["call_request_data"]["email"]}],
                    "COMMENTS": payload["call_request_data"]["additional"],
                    "SOURCE_ID": "WEB",
                    "STATUS_ID": "NEW"
                }
            )
            
            if lead_id:
                # Update call request with Bitrix lead ID
                await db.execute(
                    update(models.CallRequest)
                    .where(models.CallRequest.id == call_request_id)
                    .values(
                        bitrix_lead_id=lead_id,
                        bitrix_synced_at=datetime.now(timezone.utc)
                    )
                )
                logger.info(f"[PROCESS_LEAD] Created Bitrix lead {lead_id} for call request {call_request_id}")
                return True
            else:
                logger.error(f"[PROCESS_LEAD] Failed to create Bitrix lead for call request {call_request_id}")
                return False
                
        except Exception as e:
            logger.error(f"[PROCESS_LEAD] Error processing lead sync: {e}")
            return False
    
    async def get_sync_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get sync queue status"""
        try:
            # Count items by status
            result = await db.execute(
                select(models.BitrixSyncQueue.status, models.BitrixSyncQueue.entity_type)
            )
            items = result.all()
            
            status_counts = {}
            type_counts = {}
            
            for status, entity_type in items:
                status_counts[status] = status_counts.get(status, 0) + 1
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
            
            return {
                "status_counts": status_counts,
                "type_counts": type_counts,
                "total_items": len(items),
                "bitrix_configured": bitrix_client.is_configured()
            }
            
        except Exception as e:
            logger.error(f"[SYNC_STATUS] Error getting sync status: {e}")
            raise


# Global instance
bitrix_sync_service = BitrixSyncService()
