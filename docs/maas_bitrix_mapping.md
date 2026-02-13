# MaaS-Bitrix IDs Mapping System

## Overview

The `maas_bitrix_ids_mapping` table provides a centralized mapping system between MaaS (Manufacturing as a Service) entities and their corresponding Bitrix24 entities. This mapping enables seamless synchronization and integration between the two systems.

## Database Schema

### Table: `maas_bitrix_ids_mapping`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `maas_id` | INTEGER | MaaS entity ID (indexed) |
| `bitrix_id` | INTEGER | Bitrix24 entity ID (indexed) |
| `entity_type` | VARCHAR(20) | Entity type identifier (indexed) |
| `buffer` | JSON | Flexible storage for additional metadata |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

### Entity Types

Common entity types include:
- `deal` - MaaS orders mapped to Bitrix deals
- `contact` - MaaS users mapped to Bitrix contacts
- `lead` - MaaS call requests mapped to Bitrix leads
- `product` - MaaS services mapped to Bitrix products
- `product_row` - MaaS order items mapped to Bitrix product rows
- `invoice` - MaaS invoices mapped to Bitrix documents

## Data Model

### Python Model (`backend.models.MaasBitrixIdsMapping`)

```python
class MaasBitrixIdsMapping(Base):
    __tablename__ = 'maas_bitrix_ids_mapping'
    
    id = Column(Integer, primary_key=True, index=True)
    maas_id = Column(Integer, nullable=False, index=True)
    bitrix_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(20), nullable=False, index=True)
    buffer = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))
```

### Pydantic Schemas

#### `MaasBitrixIdsMappingCreate`
Used when creating a new mapping:
```python
{
    "maas_id": 123,
    "bitrix_id": 456,
    "entity_type": "deal",
    "buffer": {
        "sync_status": "completed",
        "notes": "Optional metadata"
    }
}
```

#### `MaasBitrixIdsMappingUpdate`
Used when updating an existing mapping:
```python
{
    "maas_id": 123,  # Optional
    "bitrix_id": 456,  # Optional
    "entity_type": "deal",  # Optional
    "buffer": {"status": "updated"}  # Optional
}
```

#### `MaasBitrixIdsMappingOut`
Response schema with all fields:
```python
{
    "id": 1,
    "maas_id": 123,
    "bitrix_id": 456,
    "entity_type": "deal",
    "buffer": {"sync_status": "completed"},
    "created_at": "2026-02-04T10:00:00Z",
    "updated_at": "2026-02-04T11:00:00Z"
}
```

## Repository Functions

### CRUD Operations

#### Create a Mapping
```python
from backend.bitrix24.repositories.mapping_repository import create_mapping

mapping = await create_mapping(
    db=db,
    maas_id=100,
    bitrix_id=5001,
    entity_type="deal",
    buffer={"sync_status": "completed"}
)
```

#### Get Mapping by MaaS ID
```python
from backend.bitrix24.repositories.mapping_repository import get_mapping_by_maas_id

mapping = await get_mapping_by_maas_id(
    db=db,
    maas_id=100,
    entity_type="deal"
)
```

#### Get Mapping by Bitrix ID
```python
from backend.bitrix24.repositories.mapping_repository import get_mapping_by_bitrix_id

mapping = await get_mapping_by_bitrix_id(
    db=db,
    bitrix_id=5001,
    entity_type="deal"
)
```

#### Update a Mapping
```python
from backend.bitrix24.repositories.mapping_repository import update_mapping

updated = await update_mapping(
    db=db,
    mapping_id=1,
    bitrix_id=5002,  # Update Bitrix ID
    buffer={"sync_status": "updated"},
    merge_buffer=True  # Merge with existing buffer data
)
```

#### Upsert (Create or Update)
```python
from backend.bitrix24.repositories.mapping_repository import upsert_mapping

mapping = await upsert_mapping(
    db=db,
    maas_id=100,
    bitrix_id=5001,
    entity_type="deal",
    buffer={"sync_status": "completed"},
    merge_buffer=True
)
```

#### Delete a Mapping
```python
from backend.bitrix24.repositories.mapping_repository import delete_mapping

success = await delete_mapping(db=db, mapping_id=1)
```

#### Delete All Mappings for an Entity
```python
from backend.bitrix24.repositories.mapping_repository import delete_mappings_by_entity

count = await delete_mappings_by_entity(
    db=db,
    maas_id=100,
    entity_type="deal"
)
```

### Query Operations

#### Get All Mappings
```python
from backend.bitrix24.repositories.mapping_repository import get_all_mappings

# Get all mappings of a specific type
mappings = await get_all_mappings(
    db=db,
    entity_type="deal",
    limit=50,
    offset=0
)

# Get all mappings (all types)
all_mappings = await get_all_mappings(db=db, limit=100)
```

### Convenience Functions

#### Get Bitrix ID for a MaaS Entity
```python
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id

bitrix_id = await get_bitrix_id(
    db=db,
    maas_id=100,
    entity_type="deal"
)
# Returns: 5001 or None if not found
```

#### Get MaaS ID for a Bitrix Entity
```python
from backend.bitrix24.repositories.mapping_repository import get_maas_id

maas_id = await get_maas_id(
    db=db,
    bitrix_id=5001,
    entity_type="deal"
)
# Returns: 100 or None if not found
```

## Buffer Field Usage

The `buffer` field is a flexible JSON column that can store additional metadata about the mapping. Common use cases include:

### Sync Status Tracking
```python
buffer = {
    "sync_status": "completed",
    "sync_timestamp": "2026-02-04T10:00:00Z",
    "sync_attempts": 1,
    "last_error": None
}
```

### Entity Metadata
```python
buffer = {
    "entity_name": "Order #123",
    "entity_status": "NEW",
    "total_price": 1500.00,
    "currency": "RUB"
}
```

### Synchronization History
```python
buffer = {
    "sync_history": [
        {
            "timestamp": "2026-02-04T10:00:00Z",
            "status": "created",
            "user": "system"
        },
        {
            "timestamp": "2026-02-04T11:00:00Z",
            "status": "updated",
            "user": "admin"
        }
    ]
}
```

### Custom Fields
```python
buffer = {
    "custom_fields": {
        "priority": "high",
        "department": "sales",
        "source": "web_portal"
    },
    "flags": {
        "requires_approval": True,
        "auto_sync": True
    }
}
```

## Integration Examples

### Example 1: Order to Deal Mapping
When creating a Bitrix deal for a MaaS order:

```python
from backend.bitrix24.repositories.mapping_repository import upsert_mapping
from backend.orders.repository import get_order_by_id

async def sync_order_to_bitrix(db, order_id: int, bitrix_deal_id: int):
    # Get order details
    order = await get_order_by_id(db, order_id)
    
    # Create mapping with order metadata
    await upsert_mapping(
        db=db,
        maas_id=order_id,
        bitrix_id=bitrix_deal_id,
        entity_type="deal",
        buffer={
            "order_status": order.status,
            "total_price": float(order.total_price) if order.total_price else None,
            "service_id": order.service_id,
            "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            "sync_type": "create"
        }
    )
```

### Example 2: User to Contact Mapping
When creating a Bitrix contact for a MaaS user:

```python
from backend.bitrix24.repositories.mapping_repository import upsert_mapping

async def sync_user_to_bitrix(db, user_id: int, bitrix_contact_id: int):
    await upsert_mapping(
        db=db,
        maas_id=user_id,
        bitrix_id=bitrix_contact_id,
        entity_type="contact",
        buffer={
            "user_type": "individual",
            "sync_timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
```

### Example 3: Finding Existing Mappings
When updating an order, check if it already has a Bitrix deal:

```python
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id

async def update_order_in_bitrix(db, order_id: int):
    # Check if order is already mapped to a deal
    bitrix_deal_id = await get_bitrix_id(db, maas_id=order_id, entity_type="deal")
    
    if bitrix_deal_id:
        # Update existing deal
        print(f"Updating Bitrix Deal {bitrix_deal_id}")
    else:
        # Create new deal
        print("Creating new Bitrix Deal")
```

## Database Initialization

The table is automatically created during application startup via the `ensure_maas_bitrix_ids_mapping_table()` function in `backend/database.py`. This function:

1. Checks if the table exists
2. Creates it if missing
3. Adds any missing columns if the table exists but is incomplete

No manual database migration is required.

## Best Practices

### 1. Use Upsert for Idempotency
Prefer `upsert_mapping()` over `create_mapping()` when you're not sure if a mapping already exists:
```python
# Good: Safe to call multiple times
await upsert_mapping(db, maas_id=100, bitrix_id=5001, entity_type="deal")

# Avoid: May fail if mapping already exists
await create_mapping(db, maas_id=100, bitrix_id=5001, entity_type="deal")
```

### 2. Buffer Merging
Use `merge_buffer=True` when updating to preserve existing metadata:
```python
# Preserves existing buffer fields
await update_mapping(
    db, 
    mapping_id=1, 
    buffer={"new_field": "value"},
    merge_buffer=True
)
```

### 3. Entity Type Consistency
Use consistent entity type strings across the application:
```python
# Good: Consistent naming
ENTITY_TYPE_DEAL = "deal"
ENTITY_TYPE_CONTACT = "contact"
ENTITY_TYPE_LEAD = "lead"

# Avoid: Inconsistent variations
"Deal", "DEAL", "deals", etc.
```

### 4. Error Handling
Always handle cases where mappings might not exist:
```python
mapping = await get_mapping_by_maas_id(db, maas_id=100, entity_type="deal")
if mapping:
    bitrix_id = mapping.bitrix_id
else:
    # Handle missing mapping
    bitrix_id = None
```

### 5. Logging
Log mapping operations for debugging and auditing:
```python
import logging

logger = logging.getLogger(__name__)

mapping = await create_mapping(...)
logger.info(f"Created mapping: {mapping.entity_type} {mapping.maas_id} <-> {mapping.bitrix_id}")
```

## Testing

Example test cases for the mapping repository:

```python
import pytest
from backend.bitrix24.repositories.mapping_repository import *

@pytest.mark.asyncio
async def test_create_mapping(db_session):
    mapping = await create_mapping(
        db=db_session,
        maas_id=1,
        bitrix_id=100,
        entity_type="deal"
    )
    assert mapping.id is not None
    assert mapping.maas_id == 1
    assert mapping.bitrix_id == 100

@pytest.mark.asyncio
async def test_get_mapping_by_maas_id(db_session):
    await create_mapping(db_session, 1, 100, "deal")
    mapping = await get_mapping_by_maas_id(db_session, 1, "deal")
    assert mapping is not None
    assert mapping.bitrix_id == 100

@pytest.mark.asyncio
async def test_upsert_creates_new(db_session):
    mapping = await upsert_mapping(db_session, 2, 200, "contact")
    assert mapping.id is not None

@pytest.mark.asyncio
async def test_upsert_updates_existing(db_session):
    await create_mapping(db_session, 3, 300, "lead")
    mapping = await upsert_mapping(db_session, 3, 301, "lead")
    assert mapping.bitrix_id == 301
```

## Future Enhancements

Potential improvements to the mapping system:

1. **Composite Indexes** - Add composite indexes on (maas_id, entity_type) and (bitrix_id, entity_type) for better query performance
2. **Soft Deletes** - Add a `deleted_at` column instead of hard deletes
3. **Audit Trail** - Track who created/modified mappings
4. **Validation** - Add constraints to ensure entity_type values are from a predefined set
5. **Bidirectional Sync Metadata** - Store sync direction and conflict resolution data in buffer

## Support

For questions or issues with the mapping system, please:
- Check the example file: `backend/bitrix24/mapping_example.py`
- Review repository functions: `backend/bitrix24/repositories/mapping_repository.py`
- Examine the data model: `backend/models.py` (MaasBitrixIdsMapping class)
