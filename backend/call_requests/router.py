"""
Call requests router
Handles call request endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend import models, schemas
from backend.core.dependencies import get_db
from backend.auth.dependencies import get_current_admin_user
from backend.call_requests.service import (
    create_call_request,
    get_call_request_by_id,
    get_all_call_requests,
    update_call_request_status,
    update_call_request_bitrix_ids
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/call-request', tags=["Call Requests"])
async def call_request_options():
    """Handle CORS preflight requests for call request"""
    return Response(status_code=200)

@router.options('/call-requests', tags=["Call Requests"])
async def call_requests_options():
    """Handle CORS preflight requests for call requests (plural)"""
    return Response(status_code=200)

@router.options('/admin/call-requests', tags=["Call Requests"])
async def admin_call_requests_options():
    """Handle CORS preflight requests for admin call requests"""
    return Response(status_code=200)

@router.options('/admin/call-requests/{call_request_id}', tags=["Call Requests"])
async def admin_call_request_options():
    """Handle CORS preflight requests for admin call request by ID"""
    return Response(status_code=200)


@router.post('/call-request', response_model=schemas.CallRequestOut, tags=["Call Requests"])
async def create_call_request_endpoint(
    call_request: schemas.CallRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new call request"""
    try:
        db_call_request = await create_call_request(db, call_request)
        logger.info(f"Call request created: {db_call_request.id}")
        return db_call_request
    except Exception as e:
        logger.error(f"Error creating call request: {e}")
        raise HTTPException(status_code=500, detail="Call request creation failed")


@router.post('/call-requests', response_model=schemas.CallRequestOut, tags=["Call Requests"])
async def create_call_request_endpoint_plural(
    call_request: schemas.CallRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new call request (plural endpoint for compatibility)"""
    try:
        db_call_request = await create_call_request(db, call_request)
        logger.info(f"Call request created: {db_call_request.id}")
        return db_call_request
    except Exception as e:
        logger.error(f"Error creating call request: {e}")
        raise HTTPException(status_code=500, detail="Call request creation failed")


# Admin endpoints
@router.get('/admin/call-requests', response_model=List[schemas.CallRequestOut], tags=["Admin", "Call Requests"])
async def list_call_requests(
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all call requests (admin only)"""
    try:
        call_requests = await get_all_call_requests(db)
        return call_requests
    except Exception as e:
        logger.error(f"Error listing call requests: {e}")
        raise HTTPException(status_code=500, detail="Failed to list call requests")


@router.get('/admin/call-requests/{call_request_id}', response_model=schemas.CallRequestOut, tags=["Admin", "Call Requests"])
async def get_call_request(
    call_request_id: int,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call request by ID (admin only)"""
    try:
        call_request = await get_call_request_by_id(db, call_request_id)
        if not call_request:
            raise HTTPException(status_code=404, detail="Call request not found")
        
        return call_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call request {call_request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get call request")


@router.put('/admin/call-requests/{call_request_id}/status', response_model=schemas.CallRequestOut, tags=["Admin", "Call Requests"])
async def update_call_request_status_endpoint(
    call_request_id: int,
    status_update: schemas.CallRequestStatusUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update call request status (admin only)"""
    try:
        call_request = await update_call_request_status(db, call_request_id, status_update.status)
        if not call_request:
            raise HTTPException(status_code=404, detail="Call request not found")
        
        return call_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating call request status {call_request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update call request status")


@router.put('/admin/call-requests/{call_request_id}/bitrix', response_model=schemas.CallRequestOut, tags=["Admin", "Call Requests"])
async def update_call_request_bitrix_endpoint(
    call_request_id: int,
    bitrix_update: schemas.CallRequestBitrixUpdate,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update call request Bitrix IDs (admin only)"""
    try:
        call_request = await update_call_request_bitrix_ids(
            db, 
            call_request_id, 
            bitrix_update.bitrix_lead_id, 
            bitrix_update.bitrix_contact_id
        )
        if not call_request:
            raise HTTPException(status_code=404, detail="Call request not found")
        
        return call_request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating call request Bitrix IDs {call_request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update call request Bitrix IDs")
