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
from backend.bitrix.client import bitrix_client
from backend.bitrix.sync_service import bitrix_sync_service
from backend.utils.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def create_call_request(db: AsyncSession, call_request: schemas.CallRequestCreate) -> models.CallRequest:
    """Create call request with Bitrix integration"""
    try:
        # Create call request
        db_call_request = await repo_create_call_request(db, call_request)
        
        # Queue Bitrix integration (non-blocking)
        try:
            await bitrix_sync_service.queue_lead_creation(db, db_call_request.id)
            # Also queue contact creation if not already synced
            await bitrix_sync_service.queue_contact_creation(db, db_call_request.user_id)
        except Exception as e:
            logger.warning(f"Failed to queue Bitrix sync for call request {db_call_request.id}: {e}")
            # Don't fail call request creation if Bitrix sync fails
        
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
    """Update call request with Bitrix IDs"""
    return await repo_update_call_request_bitrix_ids(db, call_request_id, bitrix_lead_id, bitrix_contact_id)


async def create_bitrix_lead_async(call_request_id: int):
    """Create Bitrix lead asynchronously"""
    try:
        from backend.core.dependencies import get_db
        
        # Get call request
        async for session in get_db():
            call_request = await repo_get_call_request_by_id(session, call_request_id)
            if not call_request:
                logger.warning(f"Call request {call_request_id} not found for Bitrix integration")
                return
            
            # Create Bitrix lead
            lead_id = await bitrix_client.create_lead_from_call_request(call_request)
            if lead_id:
                # Update call request with Bitrix lead ID
                await repo_update_call_request_bitrix_ids(session, call_request_id, bitrix_lead_id=lead_id)
                logger.info(f"Bitrix lead created: {lead_id} for call request {call_request_id}")
            else:
                logger.warning(f"Failed to create Bitrix lead for call request {call_request_id}")
            
            break
            
    except Exception as e:
        logger.error(f"Error creating Bitrix lead for call request {call_request_id}: {e}")


async def create_lead_from_call_request(call_request: models.CallRequest) -> Optional[int]:
    """Create Bitrix lead from call request"""
    try:
        if not bitrix_client.is_configured():
            logger.warning("Bitrix not configured, skipping lead creation")
            return None
        
        # Prepare lead fields
        lead_fields = {
            "FIELDS[TITLE]": f"Call request from {call_request.name}",
            "FIELDS[NAME]": call_request.name,
            "FIELDS[PHONE]": call_request.phone,
            "FIELDS[COMMENTS]": f"Product: {call_request.product}\nTime: {call_request.time}"
        }
        
        if call_request.additional:
            lead_fields["FIELDS[COMMENTS]"] += f"\nAdditional info: {call_request.additional}"
        
        # Create lead
        lead_id = await bitrix_client.create_lead(lead_fields)
        
        if lead_id:
            logger.info(f"Bitrix lead created: {lead_id} for call request {call_request.id}")
            return lead_id
        else:
            logger.warning(f"Failed to create Bitrix lead for call request {call_request.id}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating Bitrix lead for call request {call_request.id}: {e}")
        return None
