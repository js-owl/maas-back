"""
Call requests repository module
Database operations for call request management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas


async def create_call_request(db: AsyncSession, call_request: schemas.CallRequestCreate) -> models.CallRequest:
    """Create a new call request"""
    db_call_request = models.CallRequest(
        name=call_request.name,
        phone=call_request.phone,
        product=call_request.product,
        time=call_request.time,
        additional=call_request.additional,
        agreement=call_request.agreement
    )
    db.add(db_call_request)
    await db.commit()
    await db.refresh(db_call_request)
    return db_call_request


async def get_call_request_by_id(db: AsyncSession, call_request_id: int) -> Optional[models.CallRequest]:
    """Get call request by ID"""
    result = await db.execute(
        select(models.CallRequest).where(models.CallRequest.id == call_request_id)
    )
    return result.scalar_one_or_none()


async def get_all_call_requests(db: AsyncSession) -> List[models.CallRequest]:
    """Get all call requests (admin only)"""
    result = await db.execute(
        select(models.CallRequest).order_by(models.CallRequest.created_at.desc())
    )
    return result.scalars().all()


async def update_call_request_status(db: AsyncSession, call_request_id: int, status: str) -> Optional[models.CallRequest]:
    """Update call request status"""
    call_request = await get_call_request_by_id(db, call_request_id)
    if not call_request:
        return None
    
    call_request.status = status
    db.add(call_request)
    await db.commit()
    await db.refresh(call_request)
    return call_request


async def update_call_request_bitrix_ids(db: AsyncSession, call_request_id: int, bitrix_lead_id: int = None, bitrix_contact_id: int = None) -> Optional[models.CallRequest]:
    """Update call request with Bitrix IDs"""
    call_request = await get_call_request_by_id(db, call_request_id)
    if not call_request:
        return None
    
    if bitrix_lead_id is not None:
        call_request.bitrix_lead_id = bitrix_lead_id
    if bitrix_contact_id is not None:
        call_request.bitrix_contact_id = bitrix_contact_id
    
    db.add(call_request)
    await db.commit()
    await db.refresh(call_request)
    return call_request
