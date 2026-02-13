"""
Call requests service module
Business logic for call request management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.call_requests.repository import (
    create_call_request as repo_create_call_request,
    get_call_request_by_id as repo_get_call_request_by_id,
    get_all_call_requests as repo_get_all_call_requests,
    update_call_request_status as repo_update_call_request_status,
    update_call_request_bitrix_ids as repo_update_call_request_bitrix_ids
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def create_call_request(db: AsyncSession, call_request: schemas.CallRequestCreate) -> models.CallRequest:
    """Create call request"""
    try:
        # Create call request
        db_call_request = await repo_create_call_request(db, call_request)
        
        logger.info(f"Call request created: {db_call_request.id}")
        return db_call_request
        
    except Exception as e:
        logger.error(f"Error creating call request: {e}")
        raise


async def get_call_request_by_id(db: AsyncSession, call_request_id: int) -> Optional[models.CallRequest]:
    """Get call request by ID"""
    return await repo_get_call_request_by_id(db, call_request_id)


async def get_all_call_requests(db: AsyncSession) -> List[models.CallRequest]:
    """Get all call requests (admin only)"""
    return await repo_get_all_call_requests(db)


async def update_call_request_status(db: AsyncSession, call_request_id: int, status: str) -> Optional[models.CallRequest]:
    """Update call request status"""
    return await repo_update_call_request_status(db, call_request_id, status)


async def update_call_request_bitrix_ids(
    db: AsyncSession, 
    call_request_id: int, 
    bitrix_lead_id: int = None, 
    bitrix_contact_id: int = None
) -> Optional[models.CallRequest]:
    """Update call request with external IDs (kept for repository compatibility)"""
    return await repo_update_call_request_bitrix_ids(db, call_request_id, bitrix_lead_id, bitrix_contact_id)
