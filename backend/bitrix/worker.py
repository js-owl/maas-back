"""
Bitrix Message Worker
Consumes messages from Redis Streams and processes Bitrix operations
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.bitrix.queue_service import bitrix_queue_service
from backend.bitrix.client import bitrix_client
from backend.database import AsyncSessionLocal
from backend import models
from backend.utils.logging import get_logger
from sqlalchemy import select, update

logger = get_logger(__name__)


class BitrixWorker:
    """Worker for processing Bitrix messages from Redis Streams"""
    
    def __init__(self):
        self.running = False
        self.max_retries = 5
        self.retry_delays = [60, 300, 900, 3600, 14400]  # 1min, 5min, 15min, 1hr, 4hr
        self.batch_size = 10
        self.poll_interval = 1.0  # seconds
    
    async def process_operation_message(self, message: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Process a Bitrix operation message
        
        Args:
            message: Message from Redis Stream
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entity_type = message.get("entity_type")
            entity_id = int(message.get("entity_id", 0))
            operation = message.get("operation")
            payload = message.get("payload", {})
            retry_count = int(message.get("retry_count", "0"))
            
            logger.info(
                f"Processing {operation} operation for {entity_type} {entity_id} "
                f"(retry: {retry_count})"
            )
            
            if entity_type == "deal":
                return await self._process_deal_operation(db, entity_id, operation, payload)
            elif entity_type == "contact":
                return await self._process_contact_operation(db, entity_id, operation, payload)
            elif entity_type == "lead":
                return await self._process_lead_operation(db, entity_id, operation, payload)
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing operation message: {e}", exc_info=True)
            return False
    
    async def _process_deal_operation(
        self,
        db: AsyncSession,
        order_id: int,
        operation: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Process deal creation/update operation"""
        try:
            if operation == "create":
                # Get order and user data
                order_result = await db.execute(
                    select(models.Order).where(models.Order.order_id == order_id)
                )
                order = order_result.scalar_one_or_none()
                
                if not order:
                    logger.error(f"Order {order_id} not found")
                    return False
                
                user_result = await db.execute(
                    select(models.User).where(models.User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {order.user_id} not found for order {order_id}")
                    return False
                
                # Prepare deal data
                deal_data = {
                    "TITLE": f"Order #{order_id} - {order.service_id}",
                    "STAGE_ID": "NEW",
                    "OPPORTUNITY": str(order.total_price or 0),
                    "CURRENCY_ID": "RUB",
                    "COMMENTS": f"Service: {order.service_id}\nQuantity: {order.quantity}\nStatus: {order.status}",
                    "SOURCE_ID": "WEB",
                    "SOURCE_DESCRIPTION": "Manufacturing Service API"
                }
                
                # Add contact if available
                if user.bitrix_contact_id:
                    deal_data["CONTACT_ID"] = str(user.bitrix_contact_id)
                
                # Create deal in Bitrix
                deal_id = await bitrix_client.create_deal(
                    title=deal_data["TITLE"],
                    fields=deal_data
                )
                
                if deal_id:
                    # Update order with Bitrix deal ID
                    await db.execute(
                        update(models.Order)
                        .where(models.Order.order_id == order_id)
                        .values(bitrix_deal_id=deal_id)
                    )
                    await db.commit()
                    logger.info(f"Created Bitrix deal {deal_id} for order {order_id}")
                    return True
                else:
                    logger.error(f"Failed to create Bitrix deal for order {order_id}")
                    return False
                    
            elif operation == "update":
                # Update existing deal
                deal_id = payload.get("bitrix_deal_id")
                if not deal_id:
                    logger.error(f"No bitrix_deal_id in update payload for order {order_id}")
                    return False
                
                # Get updated order data
                order_result = await db.execute(
                    select(models.Order).where(models.Order.order_id == order_id)
                )
                order = order_result.scalar_one_or_none()
                
                if not order:
                    logger.error(f"Order {order_id} not found for update")
                    return False
                
                # Prepare update fields
                update_fields = {
                    "OPPORTUNITY": str(order.total_price or 0),
                    "COMMENTS": f"Service: {order.service_id}\nQuantity: {order.quantity}\nStatus: {order.status}"
                }
                
                # Update deal in Bitrix
                success = await bitrix_client.update_deal(deal_id, update_fields)
                if success:
                    logger.info(f"Updated Bitrix deal {deal_id} for order {order_id}")
                    return True
                else:
                    logger.error(f"Failed to update Bitrix deal {deal_id} for order {order_id}")
                    return False
            else:
                logger.error(f"Unknown deal operation: {operation}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing deal operation: {e}", exc_info=True)
            return False
    
    async def _process_contact_operation(
        self,
        db: AsyncSession,
        user_id: int,
        operation: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Process contact creation/update operation"""
        try:
            if operation == "create":
                # Get user data
                user_result = await db.execute(
                    select(models.User).where(models.User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Check if contact already exists
                if user.bitrix_contact_id:
                    logger.info(f"User {user_id} already has Bitrix contact {user.bitrix_contact_id}")
                    return True
                
                # Prepare contact data
                user_data = {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type,
                    "company": user.company,
                    "city": user.city
                }
                
                # Create contact in Bitrix
                contact_id = await bitrix_client.create_contact(user_data)
                
                if contact_id:
                    # Update user with Bitrix contact ID
                    await db.execute(
                        update(models.User)
                        .where(models.User.id == user_id)
                        .values(bitrix_contact_id=contact_id)
                    )
                    await db.commit()
                    logger.info(f"Created Bitrix contact {contact_id} for user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to create Bitrix contact for user {user_id}")
                    return False
                    
            elif operation == "update":
                # Update existing contact
                contact_id = payload.get("bitrix_contact_id")
                if not contact_id:
                    logger.error(f"No bitrix_contact_id in update payload for user {user_id}")
                    return False
                
                # Get updated user data
                user_result = await db.execute(
                    select(models.User).where(models.User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found for update")
                    return False
                
                # Prepare update fields
                user_data = {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type,
                    "company": user.company,
                    "city": user.city
                }
                
                # Note: Bitrix client doesn't have update_contact method yet
                # This would need to be implemented
                logger.warning(f"Contact update not yet implemented for user {user_id}")
                return False
            else:
                logger.error(f"Unknown contact operation: {operation}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing contact operation: {e}", exc_info=True)
            return False
    
    async def _process_lead_operation(
        self,
        db: AsyncSession,
        call_request_id: int,
        operation: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Process lead creation/update operation"""
        try:
            if operation == "create":
                # Get call request data
                cr_result = await db.execute(
                    select(models.CallRequest).where(models.CallRequest.id == call_request_id)
                )
                call_request = cr_result.scalar_one_or_none()
                
                if not call_request:
                    logger.error(f"Call request {call_request_id} not found")
                    return False
                
                # Check if lead already exists
                if call_request.bitrix_lead_id:
                    logger.info(
                        f"Call request {call_request_id} already has Bitrix lead "
                        f"{call_request.bitrix_lead_id}"
                    )
                    return True
                
                # Get user data
                user_result = await db.execute(
                    select(models.User).where(models.User.id == call_request.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                # Prepare lead data
                lead_fields = {
                    "NAME": call_request.name,
                    "PHONE": [{"VALUE": call_request.phone}],
                    "EMAIL": [{"VALUE": call_request.email}] if call_request.email else [],
                    "COMMENTS": call_request.additional or "",
                    "SOURCE_ID": "WEB",
                    "STATUS_ID": "NEW"
                }
                
                # Create lead in Bitrix
                lead_id = await bitrix_client.create_lead(
                    title=f"Call Request: {call_request.name}",
                    fields=lead_fields
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
                    await db.commit()
                    logger.info(f"Created Bitrix lead {lead_id} for call request {call_request_id}")
                    return True
                else:
                    logger.error(f"Failed to create Bitrix lead for call request {call_request_id}")
                    return False
                    
            elif operation == "update":
                # Update existing lead
                lead_id = payload.get("bitrix_lead_id")
                if not lead_id:
                    logger.error(
                        f"No bitrix_lead_id in update payload for call request {call_request_id}"
                    )
                    return False
                
                # Note: Bitrix client doesn't have update_lead method yet
                # This would need to be implemented
                logger.warning(f"Lead update not yet implemented for call request {call_request_id}")
                return False
            else:
                logger.error(f"Unknown lead operation: {operation}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing lead operation: {e}", exc_info=True)
            return False
    
    async def process_webhook_message(self, message: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Process a webhook event message
        
        Args:
            message: Message from Redis Stream
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            event_type = message.get("event_type")
            entity_type = message.get("entity_type")
            entity_id = int(message.get("entity_id", 0))
            data = message.get("data", {})
            
            logger.info(f"Processing webhook event {event_type} for {entity_type} {entity_id}")
            
            if event_type == "deal_updated":
                return await self._handle_deal_updated(db, entity_id, data)
            elif event_type == "contact_updated":
                return await self._handle_contact_updated(db, entity_id, data)
            elif event_type == "lead_updated":
                return await self._handle_lead_updated(db, entity_id, data)
            elif event_type == "invoice_generated":
                return await self._handle_invoice_generated(db, entity_id, data)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return True  # Don't fail on unknown events
                
        except Exception as e:
            logger.error(f"Error processing webhook message: {e}", exc_info=True)
            return False
    
    async def _handle_deal_updated(
        self,
        db: AsyncSession,
        deal_id: int,
        data: Dict[str, Any]
    ) -> bool:
        """Handle deal updated webhook"""
        try:
            # Find order by bitrix_deal_id
            order_result = await db.execute(
                select(models.Order).where(models.Order.bitrix_deal_id == deal_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"No order found for Bitrix deal {deal_id}")
                return True  # Not an error, just no matching order
            
            # Update order status based on deal stage if needed
            stage_id = data.get("STAGE_ID")
            if stage_id:
                # Map Bitrix stages to order statuses if needed
                # This is a placeholder - implement actual mapping logic
                logger.info(f"Deal {deal_id} stage changed to {stage_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error handling deal update: {e}", exc_info=True)
            return False
    
    async def _handle_contact_updated(
        self,
        db: AsyncSession,
        contact_id: int,
        data: Dict[str, Any]
    ) -> bool:
        """Handle contact updated webhook"""
        try:
            # Find user by bitrix_contact_id
            user_result = await db.execute(
                select(models.User).where(models.User.bitrix_contact_id == contact_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"No user found for Bitrix contact {contact_id}")
                return True  # Not an error, just no matching user
            
            # Update user data from Bitrix if needed
            logger.info(f"Contact {contact_id} updated in Bitrix")
            return True
        except Exception as e:
            logger.error(f"Error handling contact update: {e}", exc_info=True)
            return False
    
    async def _handle_lead_updated(
        self,
        db: AsyncSession,
        lead_id: int,
        data: Dict[str, Any]
    ) -> bool:
        """Handle lead updated webhook"""
        try:
            # Find call request by bitrix_lead_id
            cr_result = await db.execute(
                select(models.CallRequest).where(models.CallRequest.bitrix_lead_id == lead_id)
            )
            call_request = cr_result.scalar_one_or_none()
            
            if not call_request:
                logger.warning(f"No call request found for Bitrix lead {lead_id}")
                return True  # Not an error, just no matching call request
            
            # Update call request status based on lead status if needed
            status_id = data.get("STATUS_ID")
            if status_id:
                logger.info(f"Lead {lead_id} status changed to {status_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error handling lead update: {e}", exc_info=True)
            return False
    
    async def _handle_invoice_generated(
        self,
        db: AsyncSession,
        invoice_id: int,
        data: Dict[str, Any]
    ) -> bool:
        """Handle invoice generated webhook"""
        try:
            # TODO: Implement invoice download and storage
            logger.info(f"Invoice {invoice_id} generated in Bitrix")
            return True
        except Exception as e:
            logger.error(f"Error handling invoice generation: {e}", exc_info=True)
            return False
    
    async def process_messages(self) -> None:
        """Main worker loop - process messages from Redis Streams"""
        logger.info("Starting Bitrix worker - entering process_messages()")
        self.running = True
        
        while self.running:
            try:
                logger.debug("Worker loop iteration - checking for messages...")
                # Process operations stream
                operations_messages = await bitrix_queue_service.get_pending_messages(
                    bitrix_queue_service.operations_stream,
                    count=self.batch_size,
                    block_ms=int(self.poll_interval * 1000)
                )
                
                if operations_messages:
                    logger.info(f"Found {len(operations_messages)} operations messages to process")
                
                for message in operations_messages:
                    async with AsyncSessionLocal() as db:
                        try:
                            success = await self.process_operation_message(message, db)
                            if success:
                                await bitrix_queue_service.acknowledge_message(
                                    bitrix_queue_service.operations_stream,
                                    message["id"]
                                )
                            else:
                                # Check retry count
                                retry_count = int(message.get("retry_count", "0"))
                                if retry_count >= self.max_retries:
                                    logger.error(
                                        f"Message {message['id']} failed after {retry_count} retries, "
                                        f"acknowledging to prevent infinite loop"
                                    )
                                    await bitrix_queue_service.acknowledge_message(
                                        bitrix_queue_service.operations_stream,
                                        message["id"]
                                    )
                                # Otherwise, message will be claimed and retried later
                        except Exception as e:
                            logger.error(f"Error processing message {message.get('id')}: {e}", exc_info=True)
                
                # Process webhooks stream
                webhook_messages = await bitrix_queue_service.get_pending_messages(
                    bitrix_queue_service.webhooks_stream,
                    count=self.batch_size,
                    block_ms=0  # Non-blocking for webhooks
                )
                
                for message in webhook_messages:
                    async with AsyncSessionLocal() as db:
                        try:
                            success = await self.process_webhook_message(message, db)
                            if success:
                                await bitrix_queue_service.acknowledge_message(
                                    bitrix_queue_service.webhooks_stream,
                                    message["id"]
                                )
                        except Exception as e:
                            logger.error(f"Error processing webhook {message.get('id')}: {e}", exc_info=True)
                
                # Claim and retry pending messages periodically
                await self._retry_pending_messages()
                
            except asyncio.CancelledError:
                logger.info("Worker cancelled, shutting down")
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _retry_pending_messages(self) -> None:
        """Claim and retry pending messages that have been idle"""
        try:
            # Claim pending operations
            claimed_ops = await bitrix_queue_service.claim_pending_messages(
                bitrix_queue_service.operations_stream,
                min_idle_time_ms=60000,  # 1 minute
                count=self.batch_size
            )
            
            for message in claimed_ops:
                retry_count = int(message.get("retry_count", "0"))
                if retry_count < self.max_retries:
                    async with AsyncSessionLocal() as db:
                        try:
                            success = await self.process_operation_message(message, db)
                            if success:
                                await bitrix_queue_service.acknowledge_message(
                                    bitrix_queue_service.operations_stream,
                                    message["id"]
                                )
                            # If failed, message will be claimed again after idle time
                        except Exception as e:
                            logger.error(f"Error retrying message {message.get('id')}: {e}", exc_info=True)
                else:
                    # Max retries reached, acknowledge to prevent infinite loop
                    logger.error(
                        f"Message {message['id']} exceeded max retries, acknowledging"
                    )
                    await bitrix_queue_service.acknowledge_message(
                        bitrix_queue_service.operations_stream,
                        message["id"]
                    )
            
            # Claim pending webhooks
            claimed_webhooks = await bitrix_queue_service.claim_pending_messages(
                bitrix_queue_service.webhooks_stream,
                min_idle_time_ms=60000,
                count=self.batch_size
            )
            
            for message in claimed_webhooks:
                async with AsyncSessionLocal() as db:
                    try:
                        success = await self.process_webhook_message(message, db)
                        if success:
                            await bitrix_queue_service.acknowledge_message(
                                bitrix_queue_service.webhooks_stream,
                                message["id"]
                            )
                    except Exception as e:
                        logger.error(f"Error retrying webhook {message.get('id')}: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"Error retrying pending messages: {e}", exc_info=True)
    
    async def stop(self) -> None:
        """Stop the worker"""
        logger.info("Stopping Bitrix worker")
        self.running = False


# Global worker instance
bitrix_worker = BitrixWorker()

