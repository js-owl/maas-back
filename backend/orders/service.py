"""
Orders service module
Business logic for order creation, updates, and recalculation
"""
from typing import List, Optional, Dict, Any
import time
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.orders.repository import (
    create_order as repo_create_order,
    update_order_calc_fields as repo_update_order_calc_fields,
    get_order_by_id as repo_get_order_by_id,
    get_orders_by_user as repo_get_orders_by_user,
    get_all_orders as repo_get_all_orders,
    update_order as repo_update_order,
    delete_order as repo_delete_order,
    hard_delete_order as repo_hard_delete_order
)
from backend.files.service import get_file_data_as_base64, get_file_by_id
from backend.calculations.service import call_calculator_service
from backend.documents.service import get_documents_by_ids
from backend.bitrix.client import bitrix_client
from backend.bitrix.service import create_deal_from_order
from backend.bitrix.sync_service import bitrix_sync_service
from backend.utils.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def create_order_with_calculation(
    db: AsyncSession, 
    user_id: int, 
    order_data: schemas.OrderCreate, 
    file_id: int
) -> models.Order:
    """Create order with calculator service integration"""
    try:
        # Validate file exists
        file_record = await get_file_by_id(db, file_id)
        if not file_record:
            raise ValueError("File not found")
        
        # Get file data as base64 for calculator service
        from backend.files.service import get_file_data_as_base64
        file_data = await get_file_data_as_base64(file_record)
        file_name = file_record.original_filename or file_record.filename
        # Set correct file type for calculator service
        if file_name and file_name.lower().endswith('.stl'):
            file_type = "stl"
        elif file_name and file_name.lower().endswith(('.stp', '.step')):
            file_type = "stp"
        else:
            file_type = file_record.file_type or "application/octet-stream"
        
        # Start timing total backend processing
        total_start_time = time.time()
        
        # Start timing calculator service call specifically
        calc_service_start_time = time.time()
        
        # Call calculator service with file data
        calc_result = await call_calculator_service(
            service_id=order_data.service_id,
            material_id=order_data.material_id,
            material_form=order_data.material_form,
            quantity=order_data.quantity,
            length=order_data.length,
            width=order_data.width,
            height=order_data.height,
            n_dimensions=order_data.n_dimensions,
            dia=order_data.dia,
            tolerance_id=order_data.tolerance_id,
            finish_id=order_data.finish_id,
            cover_id=order_data.cover_id,
            k_otk=order_data.k_otk,
            k_cert=order_data.k_cert,
            timeout=10.0,
            file_data=file_data,
            file_name=file_name,
            file_type=file_type
        )
        
        # End timing calculator service call
        calc_service_end_time = time.time()
        calculation_time = calc_service_end_time - calc_service_start_time
        
        # End timing total backend processing
        total_end_time = time.time()
        total_calculation_time = total_end_time - total_start_time
        
        # Map calculation type from calculator service response
        calculation_type = "unknown"
        if calc_result.get("ml_based") is True or calc_result.get("ml_model") is not None:
            calculation_type = "ml_based"
        elif calc_result.get("rule_based") is True or calc_result.get("ml_based") is False or calc_result.get("calculation_engine") == "rule_based":
            calculation_type = "rule_based"
        elif calc_result.get("calculation_engine") == "ml_model":
            calculation_type = "ml_based"
        
        # Add calculation type fields to calc_result
        calc_result["calculation_type"] = calculation_type
        calc_result["ml_model"] = calc_result.get("ml_model")
        calc_result["ml_confidence"] = calc_result.get("ml_confidence")
        calc_result["calculation_time"] = calculation_time
        calc_result["total_calculation_time"] = total_calculation_time
        
        # Create order with calculation results
        db_order = await repo_create_order(db, user_id, order_data, file_id, calc_result)
        
        # Queue Bitrix integration (non-blocking)
        try:
            await bitrix_sync_service.queue_deal_creation(
                db, db_order.order_id, user_id, file_id, order_data.document_ids
            )
            # Also queue contact creation if not already synced
            await bitrix_sync_service.queue_contact_creation(db, user_id)
        except Exception as e:
            logger.warning(f"Failed to queue Bitrix sync for order {db_order.order_id}: {e}")
            # Don't fail order creation if Bitrix sync fails
        
        logger.info(f"Order created successfully: {db_order.order_id}")
        return db_order
        
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def create_order_with_dimensions(
    db: AsyncSession, 
    user_id: int, 
    order_data: schemas.OrderCreate
) -> models.Order:
    """Create order with dimensions only (no file)"""
    # Initialize timing variables
    calculation_time = 0.0
    total_calculation_time = 0.0
    
    try:
        # Start timing total backend processing
        total_start_time = time.time()
        
        # Start timing calculator service call specifically
        calc_service_start_time = time.time()
        
        # Call calculator service with dimensions only
        calc_result = await call_calculator_service(
            service_id=order_data.service_id,
            material_id=order_data.material_id,
            material_form=order_data.material_form,
            quantity=order_data.quantity,
            length=order_data.length,
            width=order_data.width,
            height=order_data.height,
            n_dimensions=order_data.n_dimensions,
            dia=order_data.dia,
            tolerance_id=order_data.tolerance_id,
            finish_id=order_data.finish_id,
            cover_id=order_data.cover_id,
            k_otk=order_data.k_otk,
            k_cert=order_data.k_cert,
            timeout=10.0
            # No file_data, file_name, file_type for dimensions-only
        )
        
        # End timing calculator service call
        calc_service_end_time = time.time()
        calculation_time = calc_service_end_time - calc_service_start_time
        
        # End timing total backend processing
        total_end_time = time.time()
        total_calculation_time = total_end_time - total_start_time
        
        # Map calculation type from calculator service response
        calculation_type = "unknown"
        if calc_result.get("ml_based") is True or calc_result.get("ml_model") is not None:
            calculation_type = "ml_based"
        elif calc_result.get("rule_based") is True or calc_result.get("ml_based") is False or calc_result.get("calculation_engine") == "rule_based":
            calculation_type = "rule_based"
        elif calc_result.get("calculation_engine") == "ml_model":
            calculation_type = "ml_based"
        
        # Add calculation type fields to calc_result
        calc_result["calculation_type"] = calculation_type
        calc_result["ml_model"] = calc_result.get("ml_model")
        calc_result["ml_confidence"] = calc_result.get("ml_confidence")
        calc_result["calculation_time"] = calculation_time
        calc_result["total_calculation_time"] = total_calculation_time
        
        # Create order with calculation results (no file_id)
        db_order = await repo_create_order(db, user_id, order_data, None, calc_result)
        
        # Queue Bitrix integration (non-blocking) - no file_id
        try:
            await bitrix_sync_service.queue_deal_creation(
                db, db_order.order_id, user_id, None, order_data.document_ids
            )
            # Also queue contact creation if not already synced
            await bitrix_sync_service.queue_contact_creation(db, user_id)
        except Exception as e:
            logger.warning(f"Failed to queue Bitrix sync for order {db_order.order_id}: {e}")
            # Don't fail order creation if Bitrix sync fails
        
        logger.info(f"Order created successfully with dimensions: {db_order.order_id}")
        return db_order
        
    except Exception as e:
        logger.error(f"Error creating order with dimensions: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[models.Order]:
    """Get order by ID"""
    return await repo_get_order_by_id(db, order_id)


async def get_orders_by_user(db: AsyncSession, user_id: int) -> List[models.Order]:
    """Get all orders for a user"""
    return await repo_get_orders_by_user(db, user_id)


async def get_all_orders(db: AsyncSession) -> List[models.Order]:
    """Get all orders (admin only)"""
    return await repo_get_all_orders(db)


async def update_order(db: AsyncSession, order_id: int, order_update: schemas.OrderUpdate) -> Optional[models.Order]:
    """Update order"""
    return await repo_update_order(db, order_id, order_update)


async def delete_order(db: AsyncSession, order_id: int) -> bool:
    """Cancel order (soft delete)"""
    return await repo_delete_order(db, order_id)


async def hard_delete_order(db: AsyncSession, order_id: int) -> bool:
    """Permanently delete order (admin only)"""
    return await repo_hard_delete_order(db, order_id)


async def recalculate_order_price(db: AsyncSession, order: models.Order) -> bool:
    """Recalculate order price using calculator service"""
    # Initialize timing variables
    calculation_time = 0.0
    total_calculation_time = 0.0
    
    try:
        # Start timing total backend processing
        total_start_time = time.time()
        
        # Start timing calculator service call specifically
        calc_service_start_time = time.time()
        
        # Check if order has file_id and retrieve file data
        file_data = None
        file_name = None
        file_type = None
        
        if order.file_id:
            try:
                # Get file data as base64
                file_data = await get_file_data_as_base64(db, order.file_id)
                
                # Get file record for name and type
                file_record = await get_file_by_id(db, order.file_id)
                if file_record:
                    file_name = file_record.file_name
                    # Determine file type for calculator service
                    if file_name and file_name.lower().endswith('.stl'):
                        file_type = "stl"
                    elif file_name and file_name.lower().endswith(('.stp', '.step')):
                        file_type = "stp"
                    else:
                        file_type = file_record.file_type or "application/octet-stream"
            except Exception as e:
                logger.warning(f"Could not retrieve file data for order {order.order_id}: {e}")
                # Continue without file data
        
        # Call calculator service with order parameters
        calc_result = await call_calculator_service(
            service_id=order.service_id,
            material_id=order.material_id,
            material_form=order.material_form,
            quantity=order.quantity,
            length=order.length,
            width=order.width,
            height=order.height,
            n_dimensions=order.n_dimensions,
            dia=order.dia,
            tolerance_id=order.tolerance_id,
            finish_id=order.finish_id,
            cover_id=order.cover_id,
            k_otk=order.k_otk,
            k_cert=order.k_cert,
            timeout=10.0,
            file_data=file_data,
            file_name=file_name,
            file_type=file_type
        )
        
        # End timing calculator service call
        calc_service_end_time = time.time()
        calculation_time = calc_service_end_time - calc_service_start_time
        
        # End timing total backend processing
        total_end_time = time.time()
        total_calculation_time = total_end_time - total_start_time
        
        # Add timing values to calc_result
        calc_result["calculation_time"] = calculation_time
        calc_result["total_calculation_time"] = total_calculation_time
        
        # Update order with new calculation
        await repo_update_order_calc_fields(db, order.order_id, calc_result)
        
        logger.info(f"Order {order.order_id} recalculated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error recalculating order {order.order_id}: {e}", exc_info=True)
        return False


async def create_bitrix_deal_async(order_id: int, user_id: int, file_id: int, document_ids: List[int] = None):
    """Create Bitrix deal asynchronously"""
    try:
        from backend.core.dependencies import get_db
        
        # Get order and related data
        async for session in get_db():
            order = await repo_get_order_by_id(session, order_id)
            if not order:
                logger.warning(f"Order {order_id} not found for Bitrix integration")
                return
            
            # Get file information
            file_record = await get_file_by_id(session, file_id)
            if not file_record:
                logger.warning(f"File {file_id} not found for Bitrix integration")
                return
            
            # Get documents if provided
            documents = []
            if document_ids:
                documents = await get_documents_by_ids(session, document_ids)
            
            # Create Bitrix deal
            deal_id = await create_deal_from_order(order, file_record, documents)
            if deal_id:
                logger.info(f"Bitrix deal created: {deal_id} for order {order_id}")
            else:
                logger.warning(f"Failed to create Bitrix deal for order {order_id}")
            
            break
            
    except Exception as e:
        logger.error(f"Error creating Bitrix deal for order {order_id}: {e}")


async def sync_orders_with_bitrix(db: AsyncSession) -> Dict[str, Any]:
    """Sync all orders with Bitrix (admin function)"""
    try:
        orders = await repo_get_all_orders(db)
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
                logger.error(f"Error syncing order {order.order_id} with Bitrix: {e}")
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
