"""Company DTOs for crm.company.*."""

from typing import Any

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    """Fields for creating a company (crm.company.add)."""

    # Basic information
    TITLE: str | None = None
    COMPANY_TYPE: str | None = None
    LOGO: dict | None = None

    # Address fields
    ADDRESS: str | None = None
    ADDRESS_2: str | None = None
    ADDRESS_CITY: str | None = None
    ADDRESS_POSTAL_CODE: str | None = None
    ADDRESS_REGION: str | None = None
    ADDRESS_PROVINCE: str | None = None
    ADDRESS_COUNTRY: str | None = None
    ADDRESS_COUNTRY_CODE: str | None = None
    ADDRESS_LOC_ADDR_ID: int | None = None
    ADDRESS_LEGAL: str | None = None

    # Company details
    BANKING_DETAILS: str | None = None
    INDUSTRY: str | None = None
    EMPLOYEES: str | None = None
    CURRENCY_ID: str | None = None
    REVENUE: float | None = None

    # System fields
    COMMENTS: str | None = None
    OPENED: str | None = None
    IS_MY_COMPANY: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # External source tracking
    CONTACT_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    # Multi-field values
    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow"}


class CompanyUpdate(BaseModel):
    """Fields for updating a company."""

    TITLE: str | None = None
    COMPANY_TYPE: str | None = None
    LOGO: dict | None = None

    ADDRESS: str | None = None
    ADDRESS_2: str | None = None
    ADDRESS_CITY: str | None = None
    ADDRESS_POSTAL_CODE: str | None = None
    ADDRESS_REGION: str | None = None
    ADDRESS_PROVINCE: str | None = None
    ADDRESS_COUNTRY: str | None = None
    ADDRESS_COUNTRY_CODE: str | None = None
    ADDRESS_LOC_ADDR_ID: int | None = None
    ADDRESS_LEGAL: str | None = None

    BANKING_DETAILS: str | None = None
    INDUSTRY: str | None = None
    EMPLOYEES: str | None = None
    CURRENCY_ID: str | None = None
    REVENUE: float | None = None

    COMMENTS: str | None = None
    OPENED: str | None = None
    IS_MY_COMPANY: str | None = None
    ASSIGNED_BY_ID: int | None = None

    CONTACT_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow"}


class Company(BaseModel):
    """Company entity as returned by crm.company.get / list."""

    # Read-only/system fields
    ID: int | None = None
    HAS_PHONE: str | None = None
    HAS_EMAIL: str | None = None
    HAS_IMOL: str | None = None
    CREATED_BY_ID: int | None = None
    MODIFY_BY_ID: int | None = None
    DATE_CREATE: str | None = None
    DATE_MODIFY: str | None = None
    LEAD_ID: int | None = None
    LAST_ACTIVITY_TIME: str | None = None
    LAST_ACTIVITY_BY: int | None = None

    # Basic information
    TITLE: str | None = None
    COMPANY_TYPE: str | None = None
    LOGO: dict | None = None

    # Address fields
    ADDRESS: str | None = None
    ADDRESS_2: str | None = None
    ADDRESS_CITY: str | None = None
    ADDRESS_POSTAL_CODE: str | None = None
    ADDRESS_REGION: str | None = None
    ADDRESS_PROVINCE: str | None = None
    ADDRESS_COUNTRY: str | None = None
    ADDRESS_COUNTRY_CODE: str | None = None
    ADDRESS_LOC_ADDR_ID: int | None = None
    ADDRESS_LEGAL: str | None = None

    # Company details
    BANKING_DETAILS: str | None = None
    INDUSTRY: str | None = None
    EMPLOYEES: str | None = None
    CURRENCY_ID: str | None = None
    REVENUE: float | None = None

    # System fields
    COMMENTS: str | None = None
    OPENED: str | None = None
    IS_MY_COMPANY: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # External source tracking
    CONTACT_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    # Multi-field values
    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow", "populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Full dict representation including extra fields from API."""
        data = self.model_dump(mode="json")
        extra = getattr(self, "__pydantic_extra__", None)
        if extra:
            data.update(extra)
        return data
