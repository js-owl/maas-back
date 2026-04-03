"""Address DTOs for crm.address.* methods."""

from pydantic import BaseModel


class AddressUpsert(BaseModel):
    """Fields for creating/updating a requisite address."""

    TYPE_ID: int
    ENTITY_TYPE_ID: int
    ENTITY_ID: int

    ADDRESS_1: str | None = None
    ADDRESS_2: str | None = None
    CITY: str | None = None
    POSTAL_CODE: str | None = None
    REGION: str | None = None
    PROVINCE: str | None = None
    COUNTRY: str | None = None
    COUNTRY_CODE: str | None = None
    LOC_ADDR_ID: int | None = None

    model_config = {"extra": "allow"}


class Address(BaseModel):
    """Address entity as returned by crm.address.list."""

    TYPE_ID: int | None = None
    ENTITY_TYPE_ID: int | None = None
    ENTITY_ID: int | None = None
    ANCHOR_TYPE_ID: int | None = None
    ANCHOR_ID: int | None = None

    ADDRESS_1: str | None = None
    ADDRESS_2: str | None = None
    CITY: str | None = None
    POSTAL_CODE: str | None = None
    REGION: str | None = None
    PROVINCE: str | None = None
    COUNTRY: str | None = None
    COUNTRY_CODE: str | None = None
    LOC_ADDR_ID: int | None = None

    model_config = {"extra": "allow"}
