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
from backend.utils.logging import get_logger

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
            tolerance_id=order_data.tolerance_id,
            finish_id=order_data.finish_id,
            cover_id=order_data.cover_id,
            k_otk=order_data.k_otk,
            k_cert=order_data.k_cert,
            timeout=10.0,
            file_data=file_data,
            file_name=file_name,
            file_type=file_type,
            location=order_data.location,
            document_ids=order_data.document_ids
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
        calc_result["calculation_time"] = calculation_time
        calc_result["total_calculation_time"] = total_calculation_time

        # update extracted dimensions
        extracted_dimensions = calc_result.get("extracted_dimensions", {})
        order_data.length = round(extracted_dimensions.get("length", 0), 0)
        order_data.width = round(extracted_dimensions.get("width", 0), 0)
        order_data.height = round(extracted_dimensions.get("height", 0), 0)
        
        # Create order with calculation results
        db_order = await repo_create_order(db, user_id, order_data, file_id, calc_result)
        
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
            tolerance_id=order_data.tolerance_id,
            finish_id=order_data.finish_id,
            cover_id=order_data.cover_id,
            k_otk=order_data.k_otk,
            k_cert=order_data.k_cert,
            timeout=10.0,
            location=order_data.location,
            document_ids=order_data.document_ids
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
        calc_result["calculation_time"] = calculation_time
        calc_result["total_calculation_time"] = total_calculation_time
        
        # Create order with calculation results (no file_id)
        db_order = await repo_create_order(db, user_id, order_data, None, calc_result)
        
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
    """Update order and recalculate price"""
    updated_order = await repo_update_order(db, order_id, order_update)
    
    if not updated_order:
        return None
    
    # Recalculate price after updating order fields
    # This will save the new price and calculation fields to the database
    try:
        success = await recalculate_order_price(db, updated_order)
        if not success:
            logger.warning(f"Failed to recalculate price for order {order_id}, but order was updated")
        else:
            logger.info(f"Price recalculated successfully for order {order_id}")
        
        # Always refresh order to get the latest values including price fields
        # repo_update_order_calc_fields commits the changes, so we need to refresh to see them
        updated_order = await repo_get_order_by_id(db, order_id)
        if not updated_order:
            logger.error(f"Failed to retrieve updated order {order_id} after recalculation")
    except Exception as e:
        logger.error(f"Error recalculating price for order {order_id}: {e}", exc_info=True)
        # Don't fail the update if recalculation fails, but log the error
        # Still try to refresh the order to return the latest state
        try:
            updated_order = await repo_get_order_by_id(db, order_id)
        except Exception as refresh_error:
            logger.error(f"Failed to refresh order {order_id} after recalculation error: {refresh_error}")
    
    return updated_order


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
                
                # Get file record for name and type
                file_record = await get_file_by_id(db, order.file_id)
                if file_record:
                    file_data = await get_file_data_as_base64(file_record)

                    file_name = file_record.original_filename or file_record.filename
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
            tolerance_id=order.tolerance_id,
            finish_id=order.finish_id,
            cover_id=order.cover_id,
            k_otk=order.k_otk,
            k_cert=order.k_cert,
            timeout=10.0,
            file_data=file_data,
            file_name=file_name,
            file_type=file_type,
            location=order.location
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

