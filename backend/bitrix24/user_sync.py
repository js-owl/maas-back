"""Helpers to synchronize MaaS users to Bitrix contacts/companies."""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.async_queue import enqueue_operation
from backend.bitrix24.repositories.mapping_repository import get_bitrix_id
from backend.bitrix24.sync_payload.company import (
    user_to_company_create,
    user_to_company_update,
)
from backend.bitrix24.sync_payload.contact import (
    user_to_contact_create,
    user_to_contact_update,
)
from backend.models import User
from backend.utils.logging import get_logger

logger = get_logger(__name__)


USER_ENTITY_TYPES = ("contact", "company")


def bitrix_entity_type_for_user(user: User | str) -> str:
    user_type = user if isinstance(user, str) else getattr(user, "user_type", None)
    return "company" if user_type == "legal" else "contact"


def _build_create_payload(user: User) -> tuple[str, dict]:
    entity_type = bitrix_entity_type_for_user(user)
    dto = user_to_company_create(user) if entity_type == "company" else user_to_contact_create(user)
    return entity_type, dto.model_dump(exclude_none=True)


def _build_update_payload(user: User) -> tuple[str, dict]:
    entity_type = bitrix_entity_type_for_user(user)
    dto = user_to_company_update(user) if entity_type == "company" else user_to_contact_update(user)
    return entity_type, dto.model_dump(exclude_none=True)


async def enqueue_user_create(db: AsyncSession, redis: Redis, user: User) -> None:
    entity_type, payload = _build_create_payload(user)
    await enqueue_operation(
        entity_type=entity_type,
        action="create",
        payload=payload,
        local_id=user.id,
        redis=redis,
    )


async def enqueue_user_upsert(
    db: AsyncSession,
    redis: Redis,
    user: User,
    *,
    previous_user_type: str | None = None,
) -> None:
    current_entity_type, payload = _build_update_payload(user)
    external_id = await get_bitrix_id(db, user.id, current_entity_type)
    if external_id is None:
        await enqueue_operation(
            entity_type=current_entity_type,
            action="create",
            payload=payload,
            local_id=user.id,
            redis=redis,
        )
    else:
        await enqueue_operation(
            entity_type=current_entity_type,
            action="update",
            payload=payload,
            local_id=user.id,
            external_id=external_id,
            redis=redis,
        )

    previous_entity_type = (
        bitrix_entity_type_for_user(previous_user_type)
        if previous_user_type is not None
        else None
    )
    if previous_entity_type and previous_entity_type != current_entity_type:
        # Do not automatically delete the previously synced CRM entity.
        # This protects existing CRM data and avoids races with the legal-user linked contact flow.
        return


async def enqueue_missing_users_startup_sync(db: AsyncSession, redis: Redis) -> int:
    """Enqueue create for existing non-admin, non-cancelled users that have no Bitrix mapping yet."""
    result = await db.execute(
        select(User).where(
            User.is_admin.is_(False),
            or_(User.status.is_(None), User.status != "cancelled"),
        )
    )
    users = result.scalars().all()

    enqueued = 0
    for user in users:
        entity_type = bitrix_entity_type_for_user(user)
        external_id = await get_bitrix_id(db, user.id, entity_type)
        if external_id is not None:
            continue
        await enqueue_user_create(db, redis, user)
        enqueued += 1

    logger.info(
        "Startup user sync checked %s active non-admin users; enqueued %s missing Bitrix user(s)",
        len(users),
        enqueued,
    )
    return enqueued
