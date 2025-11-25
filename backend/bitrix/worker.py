"""
Bitrix Message Worker
Consumes messages from Redis Streams and processes Bitrix operations
"""
import asyncio
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
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
                f"[WORKER] Processing {operation} operation for {entity_type} {entity_id} "
                f"(retry: {retry_count}, message_id: {message.get('id', 'unknown')})"
            )
            logger.debug(
                f"[WORKER] Message payload: {json.dumps(payload)[:200]}..."
            )
            
            result = None
            if entity_type == "deal":
                result = await self._process_deal_operation(db, entity_id, operation, payload)
            elif entity_type == "contact":
                result = await self._process_contact_operation(db, entity_id, operation, payload)
            elif entity_type == "lead":
                result = await self._process_lead_operation(db, entity_id, operation, payload)
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return False
            
            # If result is a dict with error info, update message metadata for smart retry
            if isinstance(result, dict) and "_error" in result:
                error_info = result["_error"]
                status_code = error_info.get("status_code", 0)
                error_body = error_info.get("error_body", "").lower()
                
                # Categorize error for smart retry
                if status_code == 400:
                    if "not found" in error_body:
                        error_type = "permanent"
                    elif "invalid" in error_body or "validation" in error_body:
                        error_type = "permanent"
                    else:
                        error_type = "permanent"  # Most 400 errors are permanent
                elif status_code == 401 or status_code == 403:
                    error_type = "permanent"  # Auth/permission errors
                elif status_code >= 500 or status_code == 429:
                    error_type = "transient"  # Server errors, rate limiting
                else:
                    error_type = "transient"  # Default to transient (safer to retry)
                
                # Store error type in message for retry logic (would need to update message in Redis)
                # For now, we'll handle it in the retry logic based on the error
                logger.debug(f"Error categorized as {error_type} for {entity_type} {entity_id}")
                return False
            
            return result if result is not None else False
                
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
                
                # Check if deal already exists
                if order.bitrix_deal_id:
                    logger.info(f"Order {order_id} already has Bitrix deal {order.bitrix_deal_id}, checking for duplicates...")
                    # Clean up any duplicate deals that may have been created
                    from backend.bitrix.cleanup_service import bitrix_cleanup_service
                    cleanup_result = await bitrix_cleanup_service.cleanup_duplicate_deals_for_order(db, order_id)
                    if cleanup_result["deals_deleted"] > 0:
                        logger.info(f"Cleaned up {cleanup_result['deals_deleted']} duplicate deals for order {order_id}")
                    return True
                
                # Get MaaS funnel category and stage mapping
                from backend.bitrix.funnel_manager import funnel_manager
                category_id = None
                stage_id = None
                
                # Ensure funnel is initialized (in case worker started before startup completed)
                if not funnel_manager.is_initialized():
                    logger.info("Funnel manager not initialized, initializing now...")
                    await funnel_manager.ensure_maas_funnel()
                
                # Use funnel manager if it's initialized
                if funnel_manager.is_initialized():
                    category_id = funnel_manager.get_category_id()
                    stage_id = funnel_manager.get_stage_id_for_status(order.status)
                    logger.info(f"Funnel manager initialized: category_id={category_id}, stage_id={stage_id} for order {order_id}")
                else:
                    logger.warning("Funnel manager not initialized after attempt, using default deal creation")
                
                # Prepare deal title
                deal_title = f"Order #{order_id} - {order.service_id}"
                
                # Prepare deal data (using FIELDS[...] format for Bitrix API)
                deal_data = {
                    "FIELDS[OPPORTUNITY]": str(order.total_price or 0),
                    "FIELDS[CURRENCY_ID]": "RUB",
                    "FIELDS[COMMENTS]": f"Service: {order.service_id}\nQuantity: {order.quantity}\nStatus: {order.status}",
                    "FIELDS[SOURCE_ID]": "WEB",
                    "FIELDS[SOURCE_DESCRIPTION]": "Manufacturing Service API"
                }
                
                # Add category ID if MaaS funnel is initialized
                if category_id:
                    deal_data["FIELDS[CATEGORY_ID]"] = str(category_id)
                    logger.info(f"Using MaaS funnel category ID: {category_id} for order {order_id}")
                
                # Map order status to stage ID
                if stage_id:
                    deal_data["FIELDS[STAGE_ID]"] = stage_id
                    logger.info(f"Mapped order status '{order.status}' to stage ID '{stage_id}' for order {order_id}")
                else:
                    # If no stage mapping, try to get the first stage from the category
                    # Don't set STAGE_ID - let Bitrix use the default first stage
                    logger.warning(f"No stage mapping found for order status '{order.status}', Bitrix will use default first stage for order {order_id}")
                    # Optionally, we could get the first stage from the category
                    # But it's safer to let Bitrix assign the default stage
                
                # Ensure contact exists before creating deal
                if not user.bitrix_contact_id:
                    logger.info(f"User {user.id} doesn't have Bitrix contact, creating contact first...")
                    # Queue contact creation - it will be processed by worker
                    from backend.bitrix.sync_service import bitrix_sync_service
                    await bitrix_sync_service.queue_contact_creation(db, user.id)
                    # Wait a bit for contact to be created (or check if it was created)
                    # For now, we'll create the deal without contact and update it later
                    logger.warning(f"Deal will be created without contact for order {order_id}, contact will be attached later")
                else:
                    deal_data["FIELDS[CONTACT_ID]"] = str(user.bitrix_contact_id)
                    logger.info(f"Attaching contact {user.bitrix_contact_id} to deal for order {order_id}")
                
                # Create deal in Bitrix
                deal_id = await bitrix_client.create_deal(
                    title=deal_title,
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
                # Get order and user data
                order_result = await db.execute(
                    select(models.Order).where(models.Order.order_id == order_id)
                )
                order = order_result.scalar_one_or_none()
                
                if not order:
                    logger.error(f"Order {order_id} not found for update")
                    return False
                
                # Get deal ID from order
                deal_id = order.bitrix_deal_id
                if not deal_id:
                    logger.warning(f"Order {order_id} has no Bitrix deal ID, cannot update")
                    return True  # Acknowledge - nothing to update
                
                # Check if deal exists before updating (prevent unnecessary retries for "not found" errors)
                deal = await bitrix_client.get_deal(deal_id)
                if not deal:
                    logger.warning(f"Deal {deal_id} not found in Bitrix for order {order_id} - deal may have been deleted")
                    # Deal doesn't exist - nothing to update, acknowledge immediately
                    return True
                
                # Get user to check contact
                user_result = await db.execute(
                    select(models.User).where(models.User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {order.user_id} not found for order {order_id}")
                    return False
                
                # Prepare update fields
                update_fields = {
                    "FIELDS[OPPORTUNITY]": str(order.total_price or 0),
                    "FIELDS[COMMENTS]": f"Service: {order.service_id}\nQuantity: {order.quantity}\nStatus: {order.status}"
                }
                
                # Update contact if available and not already attached
                if user.bitrix_contact_id:
                    current_contact_id = deal.get("CONTACT_ID")
                    if current_contact_id != str(user.bitrix_contact_id):
                        update_fields["FIELDS[CONTACT_ID]"] = str(user.bitrix_contact_id)
                        logger.info(f"Updating contact for deal {deal_id} to {user.bitrix_contact_id}")
                    else:
                        logger.debug(f"Contact {user.bitrix_contact_id} already attached to deal {deal_id}")
                else:
                    # Ensure contact exists
                    logger.info(f"User {user.id} doesn't have Bitrix contact, creating contact first...")
                    from backend.bitrix.sync_service import bitrix_sync_service
                    await bitrix_sync_service.queue_contact_creation(db, user.id)
                
                # Update deal in Bitrix
                result = await bitrix_client.update_deal(deal_id, update_fields)
                
                # Handle error response
                if isinstance(result, dict) and "_error" in result:
                    error_info = result["_error"]
                    status_code = error_info.get("status_code", 0)
                    error_body = error_info.get("error_body", "")
                    
                    # Check if it's a "not found" error (shouldn't happen since we checked, but handle it)
                    if status_code == 400 and "not found" in error_body.lower():
                        logger.warning(f"Deal {deal_id} not found during update (was deleted?) - acknowledging")
                        return True  # Acknowledge - deal doesn't exist
                    
                    # For other 400 errors (invalid data), return error dict for smart retry
                    if status_code == 400:
                        logger.error(f"Invalid data error updating deal {deal_id}: {error_body[:200]}")
                        # Return error dict for categorization
                        return {"_error": error_info}
                    
                    # For 500+ errors, return error dict for retry (transient)
                    if status_code >= 500:
                        logger.warning(f"Transient error updating deal {deal_id}: {status_code}")
                        return {"_error": error_info}  # Retry transient errors
                    
                    # For other errors, return error dict
                    logger.error(f"Error updating deal {deal_id}: {status_code} - {error_body[:200]}")
                    return {"_error": error_info}
                
                if not result:
                    logger.error(f"Failed to update Bitrix deal {deal_id} for order {order_id}")
                    return False
                
                # Attach file if available and not already attached
                if order.file_id:
                    from backend.files.service import get_file_by_id
                    from pathlib import Path
                    
                    file_record = await get_file_by_id(db, order.file_id)
                    if file_record and file_record.file_path:
                        file_path = Path(file_record.file_path)
                        if file_path.exists():
                            # Check if file is already attached
                            deal = await bitrix_client.get_deal(deal_id)
                            if deal:
                                file_field_code = bitrix_client.deal_file_field_code
                                file_value = deal.get(file_field_code)
                                if not file_value:
                                    # File not attached, attach it
                                    logger.info(f"Attaching file to deal {deal_id} for order {order_id}")
                                    file_attached = await bitrix_client.attach_file_to_deal(
                                        deal_id,
                                        str(file_path),
                                        file_record.original_filename or file_record.filename
                                    )
                                    if file_attached:
                                        logger.info(f"File attached to deal {deal_id} for order {order_id}")
                                    else:
                                        logger.warning(f"Failed to attach file to deal {deal_id} for order {order_id}")
                                else:
                                    logger.debug(f"File already attached to deal {deal_id} for order {order_id}")
                
                # Attach documents if available
                if order.document_ids:
                    try:
                        import json
                        from backend.documents.service import get_documents_by_ids
                        from pathlib import Path
                        
                        doc_ids = json.loads(order.document_ids) if isinstance(order.document_ids, str) else order.document_ids
                        if doc_ids:
                            documents = await get_documents_by_ids(db, doc_ids)
                            for doc in documents:
                                if doc.document_path:
                                    doc_path = Path(doc.document_path)
                                    if doc_path.exists():
                                        logger.info(f"Attaching document to deal {deal_id} for order {order_id}")
                                        await bitrix_client.attach_file_to_deal(
                                            deal_id,
                                            str(doc_path),
                                            doc.original_filename or doc.document_name
                                        )
                    except Exception as e:
                        logger.warning(f"Error attaching documents to deal {deal_id} for order {order_id}: {e}")
                
                logger.info(f"Updated Bitrix deal {deal_id} for order {order_id}")
                return True
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
                # Get user data to retrieve bitrix_contact_id
                user_result = await db.execute(
                    select(models.User).where(models.User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found for update")
                    return False
                
                contact_id = user.bitrix_contact_id
                if not contact_id:
                    logger.error(f"User {user_id} has no Bitrix contact ID, cannot update")
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
                
                # Update contact in Bitrix
                success = await bitrix_client.update_contact(contact_id, user_data)
                
                if success:
                    logger.info(f"Updated Bitrix contact {contact_id} for user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to update Bitrix contact {contact_id} for user {user_id}")
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
                from backend.bitrix.funnel_manager import funnel_manager
                
                # Map Bitrix stage ID to order status (only if funnel manager is initialized)
                mapped_status = None
                if funnel_manager.is_initialized():
                    mapped_status = funnel_manager.get_status_for_stage_id(stage_id)
                
                if mapped_status:
                    # Update order status
                    old_status = order.status
                    order.status = mapped_status
                    await db.commit()
                    await db.refresh(order)
                    logger.info(
                        f"Updated order {order.order_id} status from '{old_status}' to '{mapped_status}' "
                        f"based on Bitrix deal {deal_id} stage '{stage_id}'"
                    )
                else:
                    # Unmapped stage - log warning and leave order status unchanged
                    logger.warning(
                        f"Deal {deal_id} stage '{stage_id}' does not map to any order status. "
                        f"Order {order.order_id} status remains '{order.status}'"
                    )
            
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
        """Handle invoice generated webhook - download DOCX and convert to PDF"""
        try:
            logger.info(f"Processing invoice {invoice_id} from Bitrix")
            
            # Get invoice/document information from Bitrix
            # Try document generator API first (for invoices created via document generator)
            document_info = await bitrix_client.get_document_generator_document(invoice_id)
            
            if not document_info:
                # Fallback to old invoice API
                invoice_info = await bitrix_client.get_invoice(invoice_id)
                if not invoice_info:
                    logger.warning(f"Invoice {invoice_id} not found in Bitrix")
                    return False
                # Old API doesn't have download URL, skip
                logger.warning(f"Invoice {invoice_id} found but no download URL available (old API)")
                return False
            
            # Get download URL (prefer DOCX, fallback to PDF)
            download_url = None
            file_extension = "docx"
            
            if document_info.get("downloadUrl"):
                download_url = document_info.get("downloadUrl")
                file_extension = "docx"
            elif document_info.get("pdfUrl"):
                download_url = document_info.get("pdfUrl")
                file_extension = "pdf"
            elif document_info.get("downloadUrlMachine"):
                download_url = document_info.get("downloadUrlMachine")
                file_extension = "docx"
            elif document_info.get("pdfUrlMachine"):
                download_url = document_info.get("pdfUrlMachine")
                file_extension = "pdf"
            
            if not download_url:
                logger.warning(f"No download URL found for invoice {invoice_id}")
                return False
            
            # Get entity ID (deal ID) to find associated order
            entity_id = document_info.get("entityId")
            entity_type_id = document_info.get("entityTypeId")
            
            # entityTypeId 2 = deals
            if entity_type_id != 2 or not entity_id:
                logger.warning(f"Invoice {invoice_id} is not associated with a deal (entityTypeId: {entity_type_id})")
                return False
            
            deal_id = int(entity_id)
            
            # Find order by deal ID
            order_result = await db.execute(
                select(models.Order).where(models.Order.bitrix_deal_id == deal_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"No order found for Bitrix deal {deal_id} (invoice {invoice_id})")
                return True  # Not an error, just no matching order
            
            # Download invoice file
            invoice_dir = Path("uploads/invoices")
            invoice_dir.mkdir(parents=True, exist_ok=True)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(download_url)
                response.raise_for_status()
                
                # Save original file (DOCX or PDF)
                original_filename = f"invoice_order_{order.order_id}_deal_{deal_id}.{file_extension}"
                original_path = invoice_dir / original_filename
                
                with open(original_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded invoice {invoice_id} to {original_path}")
                
                # Convert DOCX to PDF if needed
                pdf_path = None
                if file_extension == "docx":
                    pdf_filename = f"invoice_order_{order.order_id}_deal_{deal_id}.pdf"
                    pdf_path = invoice_dir / pdf_filename
                    
                    try:
                        # Try to convert DOCX to PDF using docx2pdf
                        # This requires LibreOffice or Microsoft Word to be installed
                        from docx2pdf import convert
                        convert(str(original_path), str(pdf_path))
                        logger.info(f"Converted DOCX to PDF: {pdf_path}")
                    except ImportError:
                        logger.warning("docx2pdf not available, keeping DOCX file only")
                        pdf_path = None
                    except Exception as e:
                        logger.warning(f"Failed to convert DOCX to PDF: {e}, keeping DOCX file only")
                        pdf_path = None
                else:
                    # Already PDF
                    pdf_path = original_path
                
                # Update order with invoice info
                await db.execute(
                    update(models.Order)
                    .where(models.Order.order_id == order.order_id)
                    .values(
                        invoice_url=download_url,
                        invoice_file_path=str(pdf_path) if pdf_path else str(original_path),
                        invoice_generated_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
                
                logger.info(
                    f"Updated order {order.order_id} with invoice: "
                    f"PDF={pdf_path}, Original={original_path}"
                )
                
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading invoice {invoice_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error handling invoice generation: {e}", exc_info=True)
            return False
    
    async def process_messages(self) -> None:
        """Main worker loop - process messages from Redis Streams"""
        logger.info("Starting Bitrix worker - entering process_messages()")
        logger.info(f"Worker state before starting: running={self.running}")
        
        try:
            self.running = True
            logger.info(f"Worker state after setting: running={self.running}")
            iteration = 0
            
            logger.info("Entering worker loop...")
            while self.running:
                try:
                    iteration += 1
                    if iteration == 1 or iteration % 10 == 0:  # Log first and every 10 iterations
                        logger.info(f"Worker loop iteration {iteration} - running={self.running}")
                    logger.debug("Worker loop iteration - checking for messages...")
                    
                    # Process operations stream
                    operations_messages = await bitrix_queue_service.get_pending_messages(
                        bitrix_queue_service.operations_stream,
                        count=self.batch_size,
                        block_ms=int(self.poll_interval * 1000)
                    )
                    
                    if operations_messages:
                        logger.info(f"Found {len(operations_messages)} operations messages to process")
                    else:
                        logger.debug("No operations messages found in this iteration")
                    
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
                                    # Check retry count with smart retry logic
                                    retry_count = int(message.get("retry_count", "0"))
                                    entity_type = message.get("entity_type", "unknown")
                                    entity_id = message.get("entity_id", "unknown")
                                    operation = message.get("operation", "unknown")
                                    
                                    # Determine max retries based on error type (if stored in message)
                                    error_type = message.get("error_type", "transient")
                                    
                                    # For permanent errors (400 "not found", invalid data), use fewer retries
                                    if error_type == "permanent":
                                        max_retries_for_error = 2
                                    elif error_type == "business_logic":
                                        max_retries_for_error = 3
                                    else:
                                        max_retries_for_error = self.max_retries
                                    
                                    if retry_count >= max_retries_for_error:
                                        logger.error(
                                            f"Message {message['id']} ({entity_type} {entity_id} - {operation}) "
                                            f"failed after {retry_count} retries (max: {max_retries_for_error}), "
                                            f"acknowledging to prevent infinite loop"
                                        )
                                        await bitrix_queue_service.acknowledge_message(
                                            bitrix_queue_service.operations_stream,
                                            message["id"]
                                        )
                                    else:
                                        logger.debug(
                                            f"Message {message['id']} will be retried "
                                            f"(retry {retry_count + 1}/{max_retries_for_error})"
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
                    
                    # Small sleep to prevent tight loop if no messages
                    if not operations_messages and not webhook_messages:
                        await asyncio.sleep(0.1)
                        
                except asyncio.CancelledError:
                    logger.info("Worker cancelled, shutting down")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Error in worker loop iteration {iteration}: {e}", exc_info=True)
                    import traceback
                    logger.error(f"Worker loop traceback: {traceback.format_exc()}")
                    # Continue running after error (with delay)
                    await asyncio.sleep(self.poll_interval)
            
            logger.warning(f"Worker loop exited after {iteration} iterations - this should not happen unless worker was stopped")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error in process_messages: {e}", exc_info=True)
            import traceback
            logger.error(f"Fatal traceback: {traceback.format_exc()}")
            self.running = False
            raise
    
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

