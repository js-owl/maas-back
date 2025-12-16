"""
Orders router
Handles order creation, management, and admin endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from backend import models, schemas
from backend.core.dependencies import get_request_db as get_db
from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend.orders.service import (
    create_order_with_calculation,
    create_order_with_dimensions,
    get_order_by_id,
    get_orders_by_user,
    get_all_orders,
    update_order,
    delete_order,
    hard_delete_order,
    recalculate_order_price,
    sync_orders_with_bitrix
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/orders', tags=["Orders"])
async def orders_options():
    """Handle CORS preflight requests for orders"""
    return Response(status_code=200)

@router.options('/orders/{order_id}', tags=["Orders"])
async def order_options():
    """Handle CORS preflight requests for order by ID"""
    return Response(status_code=200)

@router.options('/admin/orders', tags=["Orders"])
async def admin_orders_options():
    """Handle CORS preflight requests for admin orders"""
    return Response(status_code=200)

@router.options('/admin/orders/{order_id}', tags=["Orders"])
async def admin_order_options():
    """Handle CORS preflight requests for admin order by ID"""
    return Response(status_code=200)

@router.options('/orders/{order_id}/documents', tags=["Orders"])
async def order_documents_options():
    """Handle CORS preflight requests for order documents"""
    return Response(status_code=200)

@router.post('/orders', response_model=schemas.OrderOut, tags=["Orders"])
async def create_order(
    request_data: schemas.OrderCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new order with JSON request body"""
    try:
        # Convert OrderCreateRequest to OrderCreate
        order_data = schemas.OrderCreate(
            service_id=request_data.service_id,
            order_name=request_data.order_name,
            quantity=request_data.quantity,
            length=request_data.length,
            width=request_data.width,
            height=request_data.height,
            thickness=request_data.thickness,
            dia=request_data.dia,
            material_id=request_data.material_id,
            material_form=request_data.material_form,
            special_instructions=request_data.special_instructions,
            tolerance_id=request_data.tolerance_id,
            finish_id=request_data.finish_id,
            cover_id=request_data.cover_id,
            k_otk=request_data.k_otk,
            k_cert=request_data.k_cert,
            n_dimensions=request_data.n_dimensions,
            location=request_data.location
        )
        
        # Create order with calculation - use appropriate function based on file_id
        if request_data.file_id is not None:
            db_order = await create_order_with_calculation(db, current_user.id, order_data, request_data.file_id)
        else:
            db_order = await create_order_with_dimensions(db, current_user.id, order_data)
        
        # Attach documents if provided
        if request_data.document_ids:
            from backend.documents.service import get_documents_by_ids
            documents = await get_documents_by_ids(db, request_data.document_ids)
            # Note: Document attachment logic would go here if needed
        
        logger.info(f"Order created: {db_order.order_id} for user {current_user.id}")
        return db_order
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Order creation failed")


@router.get('/orders', response_model=List[schemas.OrderOutSimple], tags=["Orders"])
async def list_orders(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List orders for current user"""
    try:
        orders = await get_orders_by_user(db, current_user.id)
        return orders
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to list orders")


@router.get('/orders/{order_id}', response_model=schemas.OrderOut, tags=["Orders"])
async def get_order(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get order by ID"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get order")


@router.get('/orders/{order_id}/documents', response_model=List[schemas.DocumentStorageOut], tags=["Orders"])
async def get_order_documents(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user-uploaded documents attached to an order (excludes invoices)"""
    try:
        import json
        
        # Get order
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get document IDs from order (user-uploaded technical documents only)
        if not order.document_ids:
            return []
        
        # Parse document_ids (can be JSON string or list)
        doc_ids = []
        if isinstance(order.document_ids, str):
            try:
                doc_ids = json.loads(order.document_ids)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Invalid document_ids format for order {order_id}: {order.document_ids}")
                return []
        elif isinstance(order.document_ids, list):
            doc_ids = order.document_ids
        
        if not doc_ids:
            return []
        
        # Get documents
        from backend.documents.service import get_documents_by_ids
        documents = await get_documents_by_ids(db, doc_ids)
        
        # Return all documents from document_ids (these are user-uploaded technical docs)
        user_documents = []
        for doc in documents:
            # User can access if: document is theirs, or they own the order, or they're admin
            if doc.uploaded_by == current_user.id or order.user_id == current_user.id or current_user.is_admin:
                user_documents.append(doc)
        
        return user_documents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documents for order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get order documents")


@router.put('/orders/{order_id}', response_model=schemas.OrderOut, tags=["Orders"])
async def update_order_endpoint(
    order_id: int,
    order_update: schemas.OrderUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update order"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Updating order {order_id} for user {current_user.id} with data: {order_update.dict(exclude_unset=True)}")
        
        updated_order = await update_order(db, order_id, order_update)
        if not updated_order:
            raise HTTPException(status_code=500, detail="Order update failed")
        
        logger.info(f"Order {order_id} updated successfully")
        return updated_order
    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors from Pydantic validators
        logger.error(f"Validation error updating order {order_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Order update failed")


@router.delete('/orders/{order_id}', response_model=schemas.MessageResponse, tags=["Orders"])
async def delete_order_endpoint(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel order (soft delete)"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = await delete_order(db, order_id)
        if success:
            return {"message": "Order cancelled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Order cancellation failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Order cancellation failed")


# Admin endpoints
@router.get('/admin/orders', response_model=List[schemas.OrderOut], tags=["Admin", "Orders"])
async def list_all_orders(
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all orders (admin only)"""
    try:
        orders = await get_all_orders(db)
        return orders
    except Exception as e:
        logger.error(f"Error listing all orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to list orders")


@router.get('/admin/orders/{order_id}', response_model=schemas.OrderOut, tags=["Admin", "Orders"])
async def get_admin_order(
    order_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get order by ID (admin only)"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get order")

@router.put('/admin/orders/{order_id}', response_model=schemas.MessageResponse, tags=["Admin", "Orders"])
async def update_admin_order(
    order_id: int,
    order_update: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update order status (admin only)"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update order status
        order.status = order_update.status
        await db.commit()
        await db.refresh(order)
        
        # Queue Bitrix deal update if order has a Bitrix deal
        if order.bitrix_deal_id:
            try:
                from backend.bitrix.sync_service import bitrix_sync_service
                await bitrix_sync_service.queue_deal_update(db, order_id)
            except Exception as e:
                logger.warning(f"Failed to queue Bitrix deal update for order {order_id}: {e}")
        
        logger.info(f"Admin {current_user.id} updated order {order_id} status to {order_update.status}")
        return schemas.MessageResponse(message="Order updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating admin order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update order")

@router.delete('/admin/orders/{order_id}/hard', response_model=schemas.MessageResponse, tags=["Admin", "Orders"])
async def hard_delete_order_endpoint(
    order_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete order (admin only)"""
    try:
        success = await hard_delete_order(db, order_id)
        if success:
            return {"message": "Order permanently deleted"}
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error hard deleting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Order deletion failed")


@router.post('/orders/{order_id}/recalculate', response_model=schemas.OrderOut, tags=["Orders"])
async def recalculate_order_endpoint(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Recalculate order price (individual order)"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check access permissions
        if order.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Recalculate order price
        success = await recalculate_order_price(db, order)
        if not success:
            raise HTTPException(status_code=500, detail="Order recalculation failed")
        
        # Get updated order
        updated_order = await get_order_by_id(db, order_id)
        if not updated_order:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated order")
        
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Order recalculation failed")


@router.post('/admin/orders/recalc-sync', response_model=Dict[str, Any], tags=["Admin", "Orders"])
async def recalculate_orders_sync(
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Recalculate all orders and sync with Bitrix (admin only)"""
    try:
        # Get all orders
        orders = await get_all_orders(db)
        recalculated_count = 0
        failed_count = 0
        
        for order in orders:
            try:
                success = await recalculate_order_price(db, order)
                if success:
                    recalculated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error recalculating order {order.order_id}: {e}")
                failed_count += 1
        
        # Sync with Bitrix
        bitrix_result = await sync_orders_with_bitrix(db)
        
        return {
            "total_orders": len(orders),
            "recalculated_count": recalculated_count,
            "failed_count": failed_count,
            "bitrix_sync": bitrix_result,
            "message": f"Recalculated {recalculated_count} orders and synced with Bitrix"
        }
        
    except Exception as e:
        logger.error(f"Error in order recalculation sync: {e}")
        raise HTTPException(status_code=500, detail="Order recalculation failed")


@router.get('/users/{user_id}/orders', response_model=List[schemas.OrderOutSimple], tags=["Admin", "Orders"])
async def list_user_orders(
    user_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List orders for a specific user (admin only)"""
    try:
        orders = await get_orders_by_user(db, user_id)
        return orders
    except Exception as e:
        logger.error(f"Error listing orders for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list orders")


# External API endpoint
@router.get('/api/external/orders/{order_id}/status', response_model=Dict[str, str], tags=["External API"])
async def get_order_status_external(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get order status for external systems (no auth required)"""
    try:
        order = await get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "order_id": str(order_id),
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting external order status {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get order status")
