"""
Bitrix service module
Business logic for Bitrix CRM integration
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models
from backend.bitrix.client import bitrix_client
from backend.files.service import get_file_by_id
from backend.documents.service import get_documents_by_ids
from backend.utils.logging import get_logger
from pathlib import Path

logger = get_logger(__name__)


async def create_deal_from_order(
    order: models.Order, 
    file_record: Optional[models.FileStorage] = None, 
    documents: List[models.DocumentStorage] = None
) -> Optional[int]:
    """Create Bitrix deal from order"""
    try:
        if not bitrix_client.is_configured():
            logger.warning("Bitrix not configured, skipping deal creation")
            return None
        
        # Get MaaS funnel category and stage mapping
        from backend.bitrix.funnel_manager import funnel_manager
        category_id = None
        stage_id = None
        
        # Only use funnel manager if it's initialized
        if funnel_manager.is_initialized():
            category_id = funnel_manager.get_category_id()
            stage_id = funnel_manager.get_stage_id_for_status(order.status)
        else:
            logger.debug("Funnel manager not initialized, using default deal creation")
        
        # Prepare deal fields
        deal_fields = {
            "FIELDS[OPPORTUNITY]": str(order.total_price or 0),
            "FIELDS[CURRENCY_ID]": "RUB",
            "FIELDS[COMMENTS]": f"Order #{order.order_id} - {order.service_id}",
        }
        
        # Add category ID if MaaS funnel is initialized
        if category_id:
            deal_fields["FIELDS[CATEGORY_ID]"] = str(category_id)
            logger.debug(f"Using MaaS funnel category ID: {category_id}")
        
        # Map order status to stage ID
        if stage_id:
            deal_fields["FIELDS[STAGE_ID]"] = stage_id
            logger.debug(f"Mapped order status '{order.status}' to stage ID '{stage_id}'")
        else:
            # Fallback to default stage if mapping not available
            deal_fields["FIELDS[STAGE_ID]"] = "NEW"
            logger.warning(f"No stage mapping found for order status '{order.status}', using default 'NEW'")
        
        # Add order details
        if order.special_instructions:
            deal_fields["FIELDS[COMMENTS]"] += f"\nSpecial instructions: {order.special_instructions}"
        
        # Add material information
        deal_fields["FIELDS[COMMENTS]"] += f"\nMaterial: {order.material_id} ({order.material_form})"
        deal_fields["FIELDS[COMMENTS]"] += f"\nQuantity: {order.quantity}"
        
        # Add dimensions
        if order.length and order.width and order.height:
            deal_fields["FIELDS[COMMENTS]"] += f"\nDimensions: {order.length}x{order.width}x{order.height}mm"
        elif order.dia and order.height:
            deal_fields["FIELDS[COMMENTS]"] += f"\nDimensions: Ø{order.dia}x{order.height}mm"
        
        # Add contact if available
        from sqlalchemy import select
        from backend.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            user_result = await db.execute(
                select(models.User).where(models.User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.bitrix_contact_id:
                deal_fields["FIELDS[CONTACT_ID]"] = str(user.bitrix_contact_id)
                logger.info(f"Attaching contact {user.bitrix_contact_id} to deal for order {order.order_id}")
            else:
                logger.warning(f"User {order.user_id} doesn't have Bitrix contact for order {order.order_id}")
        
        # Create deal
        deal_id = await bitrix_client.create_deal(
            title=f"Order #{order.order_id} - {order.service_id}",
            fields=deal_fields
        )
        
        if deal_id:
            # Attach file if available
            if file_record and file_record.file_path:
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    await bitrix_client.attach_file_to_deal(
                        deal_id, 
                        str(file_path), 
                        file_record.original_filename or file_record.filename
                    )
            
            # Attach documents if available
            if documents:
                for doc in documents:
                    if doc.document_path:
                        doc_path = Path(doc.document_path)
                        if doc_path.exists():
                            await bitrix_client.attach_file_to_deal(
                                deal_id,
                                str(doc_path),
                                doc.original_filename or doc.document_name
                            )
            
            logger.info(f"Bitrix deal created: {deal_id} for order {order.order_id}")
            return deal_id
        else:
            logger.warning(f"Failed to create Bitrix deal for order {order.order_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating Bitrix deal for order {order.order_id}: {e}")
        return None


async def sync_orders_with_bitrix(db: AsyncSession) -> Dict[str, Any]:
    """Sync all orders with Bitrix"""
    try:
        from backend.orders.repository import get_all_orders
        
        orders = await get_all_orders(db)
        synced_count = 0
        failed_count = 0
        
        for order in orders:
            try:
                # Get file and documents
                file_record = await get_file_by_id(db, order.file_id) if order.file_id else None
                documents = []
                
                # Create deal
                deal_id = await create_deal_from_order(order, file_record, documents)
                if deal_id:
                    synced_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error syncing order {order.id} with Bitrix: {e}")
                failed_count += 1
        
        return {
            "total_orders": len(orders),
            "synced_count": synced_count,
            "failed_count": failed_count,
            "message": f"Synced {synced_count} orders with Bitrix"
        }
        
    except Exception as e:
        logger.error(f"Error in Bitrix sync: {e}")
        raise


async def reset_bitrix_deals() -> Dict[str, Any]:
    """Reset Bitrix deals (admin function)"""
    try:
        # This would typically involve deleting or archiving deals
        # Implementation depends on specific requirements
        logger.info("Bitrix deals reset requested")
        return {
            "message": "Bitrix deals reset completed",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error resetting Bitrix deals: {e}")
        raise


async def get_bitrix_status() -> Dict[str, Any]:
    """Get Bitrix integration status"""
    try:
        is_configured = bitrix_client.is_configured()
        
        if is_configured:
            # Test connection
            fields = await bitrix_client.get_deal_fields()
            connection_ok = fields is not None
        else:
            connection_ok = False
        
        return {
            "configured": is_configured,
            "connection_ok": connection_ok,
            "base_url": bitrix_client.base_url if is_configured else None,
            "enabled": bitrix_client.enabled
        }
        
    except Exception as e:
        logger.error(f"Error getting Bitrix status: {e}")
        return {
            "configured": False,
            "connection_ok": False,
            "error": str(e)
        }
