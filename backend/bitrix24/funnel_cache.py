
"""Deal funnel (pipeline/category) cache and stage name↔code mapping.

We store:
- bitrix_category rows: local representation (name, sort, entity_type_id)
- bitrix_status rows: local representation of stages (ENTITY_ID + STATUS_ID + NAME + CATEGORY_ID)
- maas_bitrix_ids_mapping: mapping local row IDs -> Bitrix external IDs (category id, status list item id)

This module provides:
- sync_deal_funnels(): on API startup, pull current categories + stages from Bitrix and persist in sqlite.
- get_or_create_deal_category_id(): resolve by category name and create missing category in Bitrix.
- resolve_stage_name()/resolve_stage_id(): mapping between Bitrix stage codes and human names, using sqlite cache.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.dto.category import CategoryCreate
from backend.bitrix24.services.category import CategoryService
from backend.bitrix24.services.status import StatusService
from backend.bitrix24.repositories import constant_entity_repository as const_repo
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id
from backend.core.config import DEFAULT_BITRIX_CATEGORY_NAME
from backend.utils.logging import get_logger

logger = get_logger(__name__)

DEAL_ENTITY_TYPE_ID = 2


def deal_stage_entity_id(category_id: int | None, *, is_default: bool | None = None) -> str:
    """Bitrix crm.status ENTITY_ID for deal stages in a given category."""
    if is_default:
        return "DEAL_STAGE"
    if not category_id or int(category_id) == 0:
        return "DEAL_STAGE"
    return f"DEAL_STAGE_{int(category_id)}"


def _stage_code_from_parts(category_id: int | None, status_id: str) -> str:
    """Bitrix Deal.STAGE_ID format for non-default pipelines is usually C{category_id}:{STATUS_ID}."""
    if not category_id or int(category_id) == 0:
        return status_id
    return f"C{int(category_id)}:{status_id}"


def _split_stage_code(stage_id: str) -> tuple[Optional[int], str]:
    """Return (category_id_from_prefix, STATUS_ID). For 'C2:NEW' -> (2,'NEW')."""
    if not stage_id:
        return (None, stage_id)
    if ":" not in stage_id:
        return (None, stage_id)
    left, right = stage_id.split(":", 1)
    if left.startswith("C") and left[1:].isdigit():
        return (int(left[1:]), right)
    return (None, stage_id)


async def sync_deal_funnels(db: AsyncSession, client: BitrixClient) -> None:
    """Pull deal funnels + stages from Bitrix24 and upsert into local DB."""
    category_service = CategoryService(client)
    status_service = StatusService(client)

    categories = await category_service.list(DEAL_ENTITY_TYPE_ID)

    for cat in categories:
        bitrix_category_id = getattr(cat, "id", None)
        name = (getattr(cat, "name", None) or "").strip()
        if bitrix_category_id is None or not name:
            continue

        bitrix_category_id_int = int(bitrix_category_id)
        is_default = bool(getattr(cat, "isDefault", None))
        sort = getattr(cat, "sort", None)

        await const_repo.category_upsert_from_bitrix(
            db,
            entity_type_id=DEAL_ENTITY_TYPE_ID,
            name=name,
            sort=int(sort) if sort is not None else None,
            bitrix_id=bitrix_category_id_int,
            buffer={
                "is_default": is_default,
                "entity_type_id": DEAL_ENTITY_TYPE_ID,
            },
        )

        entity_id = deal_stage_entity_id(bitrix_category_id_int, is_default=is_default)
        try:
            statuses = await status_service.list({"ENTITY_ID": entity_id})
        except Exception as e:
            logger.warning("Failed to list statuses for %s (%s): %s", name, entity_id, e)
            continue

        for st in statuses:
            status_id = getattr(st, "STATUS_ID", None)
            st_name = (getattr(st, "NAME", None) or "").strip()
            if not status_id or not st_name:
                continue
            st_sort = getattr(st, "SORT", None)
            st_sem = getattr(st, "SEMANTICS", None)
            st_color = getattr(st, "COLOR", None)
            st_extra = getattr(st, "EXTRA", None)
            st_list_id = getattr(st, "ID", None)

            await const_repo.status_upsert_from_bitrix(
                db,
                entity_id=entity_id,
                status_id=str(status_id),
                name=st_name,
                category_id=bitrix_category_id_int,
                semantics=str(st_sem) if st_sem is not None else None,
                sort=int(st_sort) if st_sort is not None else None,
                color=str(st_color) if st_color is not None else None,
                extra=st_extra if isinstance(st_extra, dict) else None,
                bitrix_list_id=int(st_list_id) if st_list_id is not None else None,
                buffer={"category_bitrix_id": bitrix_category_id_int},
            )


async def get_or_create_deal_category_id(
    db: AsyncSession,
    client: BitrixClient,
    *,
    category_name: str,
) -> int:
    """Resolve Bitrix category id for a funnel by name; create it if missing."""
    name = (category_name or "").strip()
    if not name:
        name = DEFAULT_BITRIX_CATEGORY_NAME

    row = await const_repo.category_get_by_name(db, entity_type_id=DEAL_ENTITY_TYPE_ID, name=name)
    if row is not None:
        existing = await const_repo.category_get_bitrix_id(db, row.id)
        if existing is not None:
            return int(existing)

    # Create in Bitrix
    category_service = CategoryService(client)
    bitrix_id = await category_service.add(
        DEAL_ENTITY_TYPE_ID,
        CategoryCreate(entityTypeId=DEAL_ENTITY_TYPE_ID, name=name),
    )

    # Persist locally and refresh stages cache for this category.
    await const_repo.category_upsert_from_bitrix(
        db,
        entity_type_id=DEAL_ENTITY_TYPE_ID,
        name=name,
        bitrix_id=int(bitrix_id),
        buffer={"is_default": False, "entity_type_id": DEAL_ENTITY_TYPE_ID},
    )

    # Stages: new category usually gets default stages; pull them in.
    try:
        status_service = StatusService(client)
        entity_id = deal_stage_entity_id(int(bitrix_id), is_default=False)
        statuses = await status_service.list({"ENTITY_ID": entity_id})
        for st in statuses:
            status_id = getattr(st, "STATUS_ID", None)
            st_name = (getattr(st, "NAME", None) or "").strip()
            if not status_id or not st_name:
                continue
            st_list_id = getattr(st, "ID", None)
            await const_repo.status_upsert_from_bitrix(
                db,
                entity_id=entity_id,
                status_id=str(status_id),
                name=st_name,
                category_id=int(bitrix_id),
                sort=int(getattr(st, "SORT", 0) or 0),
                semantics=str(getattr(st, "SEMANTICS", None)) if getattr(st, "SEMANTICS", None) is not None else None,
                color=str(getattr(st, "COLOR", None)) if getattr(st, "COLOR", None) is not None else None,
                extra=getattr(st, "EXTRA", None) if isinstance(getattr(st, "EXTRA", None), dict) else None,
                bitrix_list_id=int(st_list_id) if st_list_id is not None else None,
                buffer={"category_bitrix_id": int(bitrix_id)},
            )
    except Exception as e:
        logger.warning("Failed to refresh stages for newly created category %s: %s", name, e)

    return int(bitrix_id)


async def resolve_stage_name(
    db: AsyncSession,
    *,
    stage_id: str | None,
    category_id: int | None,
) -> str | None:
    """Translate Bitrix deal STAGE_ID to a human name using local cache."""
    if not stage_id:
        return None

    # Try parse C{n}:{STATUS_ID} prefix
    prefix_cat, bare_status_id = _split_stage_code(str(stage_id))
    effective_category = prefix_cat if prefix_cat is not None else category_id

    # 1) direct lookup by STATUS_ID in the category entity_id
    entity_id = deal_stage_entity_id(effective_category, is_default=(not effective_category or int(effective_category) == 0))
    row = await const_repo.status_get_by_keys(db, entity_id=entity_id, status_id=str(bare_status_id))
    if row is not None and getattr(row, "name", None):
        return str(row.name)

    # 2) fallback: maybe cache stored STATUS_ID already contains prefix (rare); try as-is
    row2 = await const_repo.status_get_by_keys(db, entity_id=entity_id, status_id=str(stage_id))
    if row2 is not None and getattr(row2, "name", None):
        return str(row2.name)

    return None


async def resolve_stage_id(
    db: AsyncSession,
    *,
    stage_name: str | None,
    category_id: int | None,
) -> str | None:
    """Translate a human stage name (or bare STATUS_ID) to Bitrix deal STAGE_ID for the given category.

    Accepts:
    - stage display name (NAME in Bitrix) e.g. "Новый"
    - bare STATUS_ID e.g. "NEW"
    - full STAGE_ID e.g. "C2:NEW" (returned as-is)
    """
    if stage_name is None:
        return None
    raw = str(stage_name).strip()
    if not raw:
        return None

    # If already looks like full stage code, keep it.
    if ":" in raw and raw.upper().startswith("C"):
        return raw

    entity_id = deal_stage_entity_id(category_id, is_default=(not category_id or int(category_id) == 0))

    rows = await const_repo.status_list(db, entity_id=entity_id, limit=2000)

    # 1) match by NAME
    match = next((r for r in rows if (getattr(r, "name", "") or "").strip() == raw), None)

    # 2) fallback: match by bare STATUS_ID
    if match is None:
        match = next((r for r in rows if (getattr(r, "status_id", "") or "").strip() == raw), None)

    if match is None:
        return None

    status_id = getattr(match, "status_id", None)
    if not status_id:
        return None

    return _stage_code_from_parts(category_id, str(status_id))

