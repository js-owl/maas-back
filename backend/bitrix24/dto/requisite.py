"""Requisite DTOs for crm.requisite.* methods."""

from pydantic import BaseModel


class RequisiteCreate(BaseModel):
    """Fields for creating a universal requisite (crm.requisite.add)."""

    ENTITY_TYPE_ID: int
    ENTITY_ID: int
    PRESET_ID: int
    NAME: str

    CODE: str | None = None
    XML_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ACTIVE: str | None = None
    ADDRESS_ONLY: str | None = None
    SORT: int | None = None

    RQ_COMPANY_NAME: str | None = None
    RQ_COMPANY_FULL_NAME: str | None = None
    RQ_CONTACT: str | None = None
    RQ_EMAIL: str | None = None
    RQ_PHONE: str | None = None
    RQ_INN: str | None = None
    RQ_KPP: str | None = None
    RQ_OGRN: str | None = None

    model_config = {"extra": "allow"}


class RequisiteUpdate(BaseModel):
    """Fields for updating a universal requisite."""

    NAME: str | None = None
    CODE: str | None = None
    XML_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ACTIVE: str | None = None
    ADDRESS_ONLY: str | None = None
    SORT: int | None = None

    RQ_COMPANY_NAME: str | None = None
    RQ_COMPANY_FULL_NAME: str | None = None
    RQ_CONTACT: str | None = None
    RQ_EMAIL: str | None = None
    RQ_PHONE: str | None = None
    RQ_INN: str | None = None
    RQ_KPP: str | None = None
    RQ_OGRN: str | None = None

    model_config = {"extra": "allow"}


class Requisite(BaseModel):
    """Universal requisite entity as returned by crm.requisite.get / list."""

    ID: int | None = None
    ENTITY_TYPE_ID: int | None = None
    ENTITY_ID: int | None = None
    PRESET_ID: int | None = None
    NAME: str | None = None
    ACTIVE: str | None = None
    COUNTRY_ID: int | None = None

    RQ_COMPANY_NAME: str | None = None
    RQ_COMPANY_FULL_NAME: str | None = None
    RQ_CONTACT: str | None = None
    RQ_EMAIL: str | None = None
    RQ_PHONE: str | None = None
    RQ_INN: str | None = None
    RQ_KPP: str | None = None
    RQ_OGRN: str | None = None

    model_config = {"extra": "allow"}
