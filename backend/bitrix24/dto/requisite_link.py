"""DTOs for crm.requisite.link.* methods."""

from __future__ import annotations

from pydantic import BaseModel


class RequisiteLinkFields(BaseModel):
    """Fields for linking requisites to a CRM object."""

    ENTITY_TYPE_ID: int
    ENTITY_ID: int
    REQUISITE_ID: int
    BANK_DETAIL_ID: int
    MC_REQUISITE_ID: int = 0
    MC_BANK_DETAIL_ID: int = 0


class RequisiteLink(BaseModel):
    """Link between requisites and a CRM object."""

    ENTITY_TYPE_ID: int | None = None
    ENTITY_ID: int | None = None
    REQUISITE_ID: int | None = None
    BANK_DETAIL_ID: int | None = None
    MC_REQUISITE_ID: int | None = None
    MC_BANK_DETAIL_ID: int | None = None

    model_config = {"extra": "allow"}
