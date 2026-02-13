"""Invoice DTOs for crm.invoice.* methods."""

from typing import Any

from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    """Fields for creating an invoice (crm.invoice.add)."""

    # Required fields - Note: Many fields are marked required in Bitrix24 API
    ACCOUNT_NUMBER: str
    DATE_BILL: str  # Date of invoice issuance
    DATE_INSERT: str  # Creation date
    DATE_MARKED: str  # Date of status comment
    DATE_PAY_BEFORE: str  # Payment deadline
    ORDER_TOPIC: str  # Subject/topic
    PAY_SYSTEM_ID: int  # Payment system ID (print form)
    PAY_VOUCHER_DATE: str  # Payment document date
    PAY_VOUCHER_NUM: str  # Payment document number
    PERSON_TYPE_ID: int  # Payer type
    REASON_MARKED: str  # Status comment
    RESPONSIBLE_ID: int  # Responsible user
    STATUS_ID: str  # Invoice status
    UF_COMPANY_ID: int  # Company ID
    UF_CONTACT_ID: int  # Contact ID
    UF_MYCOMPANY_ID: int  # My company ID
    UF_DEAL_ID: int  # Deal ID
    UF_QUOTE_ID: int  # Quote ID
    USER_DESCRIPTION: str  # Comment
    PR_LOCATION: int  # Location
    INVOICE_PROPERTIES: dict[str, Any]  # Invoice properties
    PRODUCT_ROWS: list[dict[str, Any]]  # Product rows

    # Optional fields
    COMMENTS: str | None = None
    XML_ID: str | None = None
    IS_RECURRING: str | None = None

    model_config = {"extra": "allow"}


class InvoiceUpdate(BaseModel):
    """Fields for updating an invoice."""

    # Basic information
    ACCOUNT_NUMBER: str | None = None
    ORDER_TOPIC: str | None = None
    COMMENTS: str | None = None
    XML_ID: str | None = None

    # Dates
    DATE_BILL: str | None = None
    DATE_INSERT: str | None = None
    DATE_MARKED: str | None = None
    DATE_PAY_BEFORE: str | None = None
    PAY_VOUCHER_DATE: str | None = None

    # Status
    STATUS_ID: str | None = None
    REASON_MARKED: str | None = None

    # Payment information
    PAY_SYSTEM_ID: int | None = None
    PAY_VOUCHER_NUM: str | None = None
    PERSON_TYPE_ID: int | None = None

    # Relationships
    RESPONSIBLE_ID: int | None = None
    UF_COMPANY_ID: int | None = None
    UF_CONTACT_ID: int | None = None
    UF_MYCOMPANY_ID: int | None = None
    UF_DEAL_ID: int | None = None
    UF_QUOTE_ID: int | None = None

    # Additional
    USER_DESCRIPTION: str | None = None
    PR_LOCATION: int | None = None
    IS_RECURRING: str | None = None
    INVOICE_PROPERTIES: dict[str, Any] | None = None
    PRODUCT_ROWS: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class Invoice(BaseModel):
    """Invoice entity as returned by crm.invoice.get / list."""

    # Read-only fields
    ID: int | None = None
    CURRENCY: str | None = None
    DATE_PAYED: str | None = None
    DATE_STATUS: str | None = None
    DATE_UPDATE: str | None = None
    CREATED_BY: int | None = None
    EMP_PAYED_ID: int | None = None
    EMP_STATUS_ID: int | None = None
    LID: str | None = None
    PAYED: str | None = None
    PRICE: float | None = None
    TAX_VALUE: float | None = None

    # Responsible user details (read-only)
    RESPONSIBLE_EMAIL: str | None = None
    RESPONSIBLE_LAST_NAME: str | None = None
    RESPONSIBLE_LOGIN: str | None = None
    RESPONSIBLE_NAME: str | None = None
    RESPONSIBLE_PERSONAL_PHOTO: int | None = None
    RESPONSIBLE_SECOND_NAME: str | None = None
    RESPONSIBLE_WORK_POSITION: str | None = None

    # Basic information
    ACCOUNT_NUMBER: str | None = None
    ORDER_TOPIC: str | None = None
    COMMENTS: str | None = None
    XML_ID: str | None = None

    # Dates
    DATE_BILL: str | None = None
    DATE_INSERT: str | None = None
    DATE_MARKED: str | None = None
    DATE_PAY_BEFORE: str | None = None
    PAY_VOUCHER_DATE: str | None = None

    # Status
    STATUS_ID: str | None = None
    REASON_MARKED: str | None = None

    # Payment information
    PAY_SYSTEM_ID: int | None = None
    PAY_VOUCHER_NUM: str | None = None
    PERSON_TYPE_ID: int | None = None

    # Relationships
    RESPONSIBLE_ID: int | None = None
    UF_COMPANY_ID: int | None = None
    UF_CONTACT_ID: int | None = None
    UF_MYCOMPANY_ID: int | None = None
    UF_DEAL_ID: int | None = None
    UF_QUOTE_ID: int | None = None

    # Additional
    USER_DESCRIPTION: str | None = None
    PR_LOCATION: int | None = None
    IS_RECURRING: str | None = None
    INVOICE_PROPERTIES: dict[str, Any] | None = None
    PRODUCT_ROWS: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
