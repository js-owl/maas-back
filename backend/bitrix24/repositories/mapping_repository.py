"""
MaaS-Bitrix IDs Mapping Repository
Database operations for entity ID mapping between MaaS and Bitrix24
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete as sql_delete
from backend.models import MaasBitrixIdsMapping
from backend.utils.logging import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)


async def create_mapping(
    db: AsyncSession,
    maas_id: int,
    bitrix_id: int,
    entity_type: str,
    buffer: Optional[Dict[str, Any]] = None
) -> MaasBitrixIdsMapping:
    """
    Create a new ID mapping between MaaS and Bitrix entities
    
    Args:
        db: Database session
        maas_id: MaaS entity ID
        bitrix_id: Bitrix entity ID
        entity_type: Type of entity (e.g., 'deal', 'contact', 'lead', 'product')
        buffer: Optional JSON buffer for additional data
        
    Returns:
        Created mapping record
    """
    mapping = MaasBitrixIdsMapping(
        maas_id=maas_id,
        bitrix_id=bitrix_id,
        entity_type=entity_type,
        buffer=buffer
    )
    
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    
    logger.info(f"Created mapping: {entity_type} MaaS ID {maas_id} <-> Bitrix ID {bitrix_id}")
    return mapping


async def get_mapping_by_id(db: AsyncSession, mapping_id: int) -> Optional[MaasBitrixIdsMapping]:
    """
    Get mapping by its primary key ID
    
    Args:
        db: Database session
        mapping_id: Primary key ID of the mapping
        
    Returns:
        Mapping record or None
    """
    result = await db.execute(
        select(MaasBitrixIdsMapping).where(MaasBitrixIdsMapping.id == mapping_id)
    )
    return result.scalar_one_or_none()


async def get_mapping_by_maas_id(
    db: AsyncSession,
    maas_id: int,
    entity_type: str
) -> Optional[MaasBitrixIdsMapping]:
    """
    Get mapping by MaaS ID and entity type
    
    Args:
        db: Database session
        maas_id: MaaS entity ID
        entity_type: Type of entity
        
    Returns:
        Mapping record or None
    """
    result = await db.execute(
        select(MaasBitrixIdsMapping).where(
            and_(
                MaasBitrixIdsMapping.maas_id == maas_id,
                MaasBitrixIdsMapping.entity_type == entity_type
            )
        )
    )
    return result.scalar_one_or_none()


async def get_mapping_by_bitrix_id(
    db: AsyncSession,
    bitrix_id: int,
    entity_type: str
) -> Optional[MaasBitrixIdsMapping]:
    """
    Get mapping by Bitrix ID and entity type
    
    Args:
        db: Database session
        bitrix_id: Bitrix entity ID
        entity_type: Type of entity
        
    Returns:
        Mapping record or None
    """
    result = await db.execute(
        select(MaasBitrixIdsMapping).where(
            and_(
                MaasBitrixIdsMapping.bitrix_id == bitrix_id,
                MaasBitrixIdsMapping.entity_type == entity_type
            )
        )
    )
    return result.scalar_one_or_none()


async def get_all_mappings(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[MaasBitrixIdsMapping]:
    """
    Get all mappings with optional filtering
    
    Args:
        db: Database session
        entity_type: Optional filter by entity type
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of mapping records
    """
    query = select(MaasBitrixIdsMapping)
    
    if entity_type:
        query = query.where(MaasBitrixIdsMapping.entity_type == entity_type)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_mapping(
    db: AsyncSession,
    mapping_id: int,
    maas_id: Optional[int] = None,
    bitrix_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    buffer: Optional[Dict[str, Any]] = None,
    merge_buffer: bool = False
) -> Optional[MaasBitrixIdsMapping]:
    """
    Update an existing mapping
    
    Args:
        db: Database session
        mapping_id: Primary key ID of the mapping
        maas_id: New MaaS ID (optional)
        bitrix_id: New Bitrix ID (optional)
        entity_type: New entity type (optional)
        buffer: New buffer data (optional)
        merge_buffer: If True, merge buffer with existing data instead of replacing
        
    Returns:
        Updated mapping record or None if not found
    """
    mapping = await get_mapping_by_id(db, mapping_id)
    if not mapping:
        logger.warning(f"Mapping with ID {mapping_id} not found")
        return None
    
    if maas_id is not None:
        mapping.maas_id = maas_id
    
    if bitrix_id is not None:
        mapping.bitrix_id = bitrix_id
    
    if entity_type is not None:
        mapping.entity_type = entity_type
    
    if buffer is not None:
        if merge_buffer and mapping.buffer:
            # Merge with existing buffer
            existing_buffer = mapping.buffer if isinstance(mapping.buffer, dict) else {}
            mapping.buffer = {**existing_buffer, **buffer}
        else:
            # Replace buffer
            mapping.buffer = buffer
    
    mapping.updated_at = datetime.now(timezone.utc)
    
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    
    logger.info(f"Updated mapping ID {mapping_id}")
    return mapping


async def upsert_mapping(
    db: AsyncSession,
    maas_id: int,
    bitrix_id: int,
    entity_type: str,
    buffer: Optional[Dict[str, Any]] = None,
    merge_buffer: bool = False
) -> MaasBitrixIdsMapping:
    """
    Create or update a mapping based on MaaS ID and entity type
    
    Args:
        db: Database session
        maas_id: MaaS entity ID
        bitrix_id: Bitrix entity ID
        entity_type: Type of entity
        buffer: Optional buffer data
        merge_buffer: If True and record exists, merge buffer with existing data
        
    Returns:
        Created or updated mapping record
    """
    existing = await get_mapping_by_maas_id(db, maas_id, entity_type)
    
    if existing:
        # Update existing mapping
        return await update_mapping(
            db,
            existing.id,
            bitrix_id=bitrix_id,
            buffer=buffer,
            merge_buffer=merge_buffer
        )
    else:
        # Create new mapping
        return await create_mapping(db, maas_id, bitrix_id, entity_type, buffer)


async def delete_mapping(db: AsyncSession, mapping_id: int) -> bool:
    """
    Delete a mapping by its primary key ID
    
    Args:
        db: Database session
        mapping_id: Primary key ID of the mapping
        
    Returns:
        True if deleted, False if not found
    """
    mapping = await get_mapping_by_id(db, mapping_id)
    if not mapping:
        logger.warning(f"Mapping with ID {mapping_id} not found")
        return False
    
    await db.delete(mapping)
    await db.commit()
    
    logger.info(f"Deleted mapping ID {mapping_id}")
    return True


async def delete_mappings_by_entity(
    db: AsyncSession,
    maas_id: int,
    entity_type: str
) -> int:
    """
    Delete all mappings for a specific MaaS entity
    
    Args:
        db: Database session
        maas_id: MaaS entity ID
        entity_type: Type of entity
        
    Returns:
        Number of deleted records
    """
    result = await db.execute(
        sql_delete(MaasBitrixIdsMapping).where(
            and_(
                MaasBitrixIdsMapping.maas_id == maas_id,
                MaasBitrixIdsMapping.entity_type == entity_type
            )
        )
    )
    await db.commit()
    
    deleted_count = result.rowcount
    logger.info(f"Deleted {deleted_count} mapping(s) for {entity_type} MaaS ID {maas_id}")
    return deleted_count


async def get_bitrix_id(
    db: AsyncSession,
    maas_id: int,
    entity_type: str
) -> Optional[int]:
    """
    Convenience method to get Bitrix ID for a MaaS entity
    
    Args:
        db: Database session
        maas_id: MaaS entity ID
        entity_type: Type of entity
        
    Returns:
        Bitrix ID or None if not found
    """
    mapping = await get_mapping_by_maas_id(db, maas_id, entity_type)
    return mapping.bitrix_id if mapping else None


async def get_maas_id(
    db: AsyncSession,
    bitrix_id: int,
    entity_type: str
) -> Optional[int]:
    """
    Convenience method to get MaaS ID for a Bitrix entity
    
    Args:
        db: Database session
        bitrix_id: Bitrix entity ID
        entity_type: Type of entity
        
    Returns:
        MaaS ID or None if not found
    """
    mapping = await get_mapping_by_bitrix_id(db, bitrix_id, entity_type)
    return mapping.maas_id if mapping else None
