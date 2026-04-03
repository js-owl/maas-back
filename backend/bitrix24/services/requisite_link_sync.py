"""Helpers to register Bitrix requisite links for deals and invoices."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.constants import EntityTypeId
from backend.bitrix24.dto.requisite_link import RequisiteLinkFields
from backend.bitrix24.repositories.mapping_repository import (
    get_bitrix_id,
    get_mapping_by_bitrix_id,
    get_mapping_by_maas_id,
)
from backend.bitrix24.services.invoice import InvoiceService
from backend.bitrix24.services.requisite_link import RequisiteLinkService
from backend.models import Kit, User
from backend.utils.logging import get_logger

logger = get_logger(__name__)

_ENV_MC_REQUISITE_ID = "BITRIX_MYCOMPANY_REQUISITE_ID"
_ENV_MC_BANK_DETAIL_ID = "BITRIX_MYCOMPANY_BANK_DETAIL_ID"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_int_env(name: str, default: int = 0) -> int:
    return _safe_int(os.getenv(name), default)


async def _resolve_client_link_values(db: AsyncSession, user: User) -> tuple[int, int]:
    requisite_id = 0
    bank_detail_id = 0

    if getattr(user, "user_type", None) == "legal":
        company_mapping = await get_mapping_by_maas_id(db, user.id, "company")
        buffer = company_mapping.buffer if company_mapping and isinstance(company_mapping.buffer, dict) else {}
        requisite_id = _safe_int(buffer.get("client_requisite_id"))
        bank_detail_id = _safe_int(buffer.get("client_bank_detail_id"))
        if not requisite_id:
            requisite_id = _safe_int(await get_bitrix_id(db, user.id, "company_requisite"))
        if not bank_detail_id:
            bank_detail_id = _safe_int(await get_bitrix_id(db, user.id, "company_bank_detail"))
    else:
        requisite_id = _safe_int(await get_bitrix_id(db, user.id, "contact_requisite"))
        bank_detail_id = 0

    return requisite_id, bank_detail_id


async def _resolve_seller_link_values(*, invoice_has_mycompany: bool) -> tuple[int, int]:
    if not invoice_has_mycompany:
        return 0, 0
    return (
        _safe_int_env(_ENV_MC_REQUISITE_ID, 0),
        _safe_int_env(_ENV_MC_BANK_DETAIL_ID, 0),
    )


async def _register_link(
    client: BitrixClient,
    *,
    entity_type_id: int,
    entity_id: int,
    requisite_id: int,
    bank_detail_id: int,
    mc_requisite_id: int,
    mc_bank_detail_id: int,
) -> bool:
    if not any((requisite_id, bank_detail_id, mc_requisite_id, mc_bank_detail_id)):
        logger.debug(
            "Skipping requisite link registration for entityTypeId=%s entityId=%s because all link ids are zero",
            entity_type_id,
            entity_id,
        )
        return False

    svc = RequisiteLinkService(client)
    return await svc.register(
        RequisiteLinkFields(
            ENTITY_TYPE_ID=int(entity_type_id),
            ENTITY_ID=int(entity_id),
            REQUISITE_ID=int(requisite_id),
            BANK_DETAIL_ID=int(bank_detail_id),
            MC_REQUISITE_ID=int(mc_requisite_id),
            MC_BANK_DETAIL_ID=int(mc_bank_detail_id),
        )
    )


async def sync_deal_requisite_link(
    db: AsyncSession,
    client: BitrixClient,
    *,
    kit_id: int,
    deal_id: int,
) -> bool:
    kit = await db.get(Kit, int(kit_id))
    if kit is None:
        logger.warning("Skipping deal requisite link sync: kit_id=%s not found", kit_id)
        return False

    user = await db.get(User, int(kit.user_id)) if getattr(kit, "user_id", None) is not None else None
    if user is None:
        logger.warning("Skipping deal requisite link sync: no user for kit_id=%s", kit_id)
        return False

    requisite_id, bank_detail_id = await _resolve_client_link_values(db, user)
    mc_requisite_id, mc_bank_detail_id = await _resolve_seller_link_values(invoice_has_mycompany=False)

    registered = await _register_link(
        client,
        entity_type_id=int(EntityTypeId.DEAL),
        entity_id=int(deal_id),
        requisite_id=int(requisite_id),
        bank_detail_id=int(bank_detail_id),
        mc_requisite_id=int(mc_requisite_id),
        mc_bank_detail_id=int(mc_bank_detail_id),
    )
    if registered:
        logger.info(
            "Registered Bitrix requisite link for deal_id=%s kit_id=%s user_id=%s requisite_id=%s bank_detail_id=%s",
            deal_id,
            kit_id,
            user.id,
            requisite_id,
            bank_detail_id,
        )
    return registered


async def _resolve_user_id_for_invoice(
    db: AsyncSession,
    *,
    company_id: Any = None,
    contact_id: Any = None,
    deal_id: Any = None,
) -> int | None:
    company_bitrix_id = _safe_int(company_id, 0)
    if company_bitrix_id:
        mapping = await get_mapping_by_bitrix_id(db, company_bitrix_id, "company")
        if mapping is not None:
            return int(mapping.maas_id)

    contact_bitrix_id = _safe_int(contact_id, 0)
    if contact_bitrix_id:
        mapping = await get_mapping_by_bitrix_id(db, contact_bitrix_id, "contact")
        if mapping is not None:
            return int(mapping.maas_id)

    deal_bitrix_id = _safe_int(deal_id, 0)
    if deal_bitrix_id:
        mapping = await get_mapping_by_bitrix_id(db, deal_bitrix_id, "deal")
        if mapping is not None:
            kit = await db.get(Kit, int(mapping.maas_id))
            if kit is not None and getattr(kit, "user_id", None) is not None:
                return int(kit.user_id)

    return None


async def sync_invoice_requisite_link(
    db: AsyncSession,
    client: BitrixClient,
    *,
    invoice_id: int,
    payload: dict[str, Any] | None = None,
) -> bool:
    payload = dict(payload or {})
    company_id = payload.get("UF_COMPANY_ID")
    contact_id = payload.get("UF_CONTACT_ID")
    deal_id = payload.get("UF_DEAL_ID")
    mycompany_id = payload.get("UF_MYCOMPANY_ID")

    if not any(v is not None for v in (company_id, contact_id, deal_id, mycompany_id)):
        try:
            invoice = await InvoiceService(client).get(int(invoice_id))
            invoice_data = invoice.model_dump(exclude_none=True)
            company_id = invoice_data.get("UF_COMPANY_ID")
            contact_id = invoice_data.get("UF_CONTACT_ID")
            deal_id = invoice_data.get("UF_DEAL_ID")
            mycompany_id = invoice_data.get("UF_MYCOMPANY_ID")
        except Exception as exc:
            logger.warning("Failed to fetch invoice %s for requisite link resolution: %s", invoice_id, exc)

    user_id = await _resolve_user_id_for_invoice(
        db,
        company_id=company_id,
        contact_id=contact_id,
        deal_id=deal_id,
    )
    if user_id is None:
        logger.warning(
            "Skipping invoice requisite link sync: unable to resolve MaaS user for invoice_id=%s company_id=%s contact_id=%s deal_id=%s",
            invoice_id,
            company_id,
            contact_id,
            deal_id,
        )
        return False

    user = await db.get(User, int(user_id))
    if user is None:
        logger.warning("Skipping invoice requisite link sync: MaaS user_id=%s not found", user_id)
        return False

    requisite_id, bank_detail_id = await _resolve_client_link_values(db, user)
    mc_requisite_id, mc_bank_detail_id = await _resolve_seller_link_values(
        invoice_has_mycompany=bool(_safe_int(mycompany_id, 0))
    )

    registered = await _register_link(
        client,
        entity_type_id=int(EntityTypeId.INVOICE),
        entity_id=int(invoice_id),
        requisite_id=int(requisite_id),
        bank_detail_id=int(bank_detail_id),
        mc_requisite_id=int(mc_requisite_id),
        mc_bank_detail_id=int(mc_bank_detail_id),
    )
    if registered:
        logger.info(
            "Registered Bitrix requisite link for invoice_id=%s user_id=%s requisite_id=%s bank_detail_id=%s",
            invoice_id,
            user.id,
            requisite_id,
            bank_detail_id,
        )
    return registered
