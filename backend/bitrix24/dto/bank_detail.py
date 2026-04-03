"""Bank detail DTOs for crm.requisite.bankdetail.* methods."""

from pydantic import BaseModel


class BankDetailCreate(BaseModel):
    """Fields for creating a bank detail."""

    ENTITY_ID: int
    COUNTRY_ID: int | None = None
    NAME: str | None = None
    CODE: str | None = None
    XML_ID: str | None = None
    ACTIVE: str | None = None
    SORT: int | None = None

    RQ_BANK_NAME: str | None = None
    RQ_BIK: str | None = None
    RQ_ACC_NUM: str | None = None
    RQ_COR_ACC_NUM: str | None = None
    RQ_SWIFT: str | None = None
    RQ_IBAN: str | None = None
    RQ_ACC_CURRENCY: str | None = None

    model_config = {"extra": "allow"}


class BankDetailUpdate(BaseModel):
    """Fields for updating a bank detail."""

    COUNTRY_ID: int | None = None
    NAME: str | None = None
    CODE: str | None = None
    XML_ID: str | None = None
    ACTIVE: str | None = None
    SORT: int | None = None

    RQ_BANK_NAME: str | None = None
    RQ_BIK: str | None = None
    RQ_ACC_NUM: str | None = None
    RQ_COR_ACC_NUM: str | None = None
    RQ_SWIFT: str | None = None
    RQ_IBAN: str | None = None
    RQ_ACC_CURRENCY: str | None = None

    model_config = {"extra": "allow"}


class BankDetail(BaseModel):
    """Bank detail entity as returned by crm.requisite.bankdetail.get / list."""

    ID: int | None = None
    ENTITY_ID: int | None = None
    COUNTRY_ID: int | None = None
    NAME: str | None = None
    ACTIVE: str | None = None

    RQ_BANK_NAME: str | None = None
    RQ_BIK: str | None = None
    RQ_ACC_NUM: str | None = None
    RQ_COR_ACC_NUM: str | None = None
    RQ_SWIFT: str | None = None
    RQ_IBAN: str | None = None
    RQ_ACC_CURRENCY: str | None = None

    model_config = {"extra": "allow"}
