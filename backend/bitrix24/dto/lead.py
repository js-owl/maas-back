"""Lead DTOs for crm.lead.* methods."""

from pydantic import BaseModel


class LeadCreate(BaseModel):
    """Fields for creating a lead (crm.lead.add)."""

    # Basic information
    TITLE: str | None = None
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    BIRTHDATE: str | None = None
    COMPANY_TITLE: str | None = None
    POST: str | None = None

    # Status and source
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    STATUS_ID: str | None = None
    STATUS_DESCRIPTION: str | None = None

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

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None

    # System fields
    OPENED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    # Multi-field values (contact methods)
    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow"}


class LeadUpdate(BaseModel):
    """Fields for updating a lead."""

    # Basic information
    TITLE: str | None = None
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    BIRTHDATE: str | None = None
    COMPANY_TITLE: str | None = None
    POST: str | None = None

    # Status and source
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    STATUS_ID: str | None = None
    STATUS_DESCRIPTION: str | None = None

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

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None

    # System fields
    OPENED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    # Multi-field values (contact methods)
    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow"}


class Lead(BaseModel):
    """Lead entity as returned by crm.lead.get / list."""

    # Read-only fields
    ID: int | None = None
    STATUS_SEMANTIC_ID: str | None = None
    HAS_PHONE: str | None = None
    HAS_EMAIL: str | None = None
    HAS_IMOL: str | None = None
    CREATED_BY_ID: int | None = None
    MODIFY_BY_ID: int | None = None
    MOVED_BY_ID: int | None = None
    DATE_CREATE: str | None = None
    DATE_MODIFY: str | None = None
    MOVED_TIME: str | None = None
    IS_RETURN_CUSTOMER: str | None = None
    DATE_CLOSED: str | None = None
    LAST_ACTIVITY_TIME: str | None = None
    LAST_ACTIVITY_BY: int | None = None

    # Basic information
    TITLE: str | None = None
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    BIRTHDATE: str | None = None
    COMPANY_TITLE: str | None = None
    POST: str | None = None

    # Status and source
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    STATUS_ID: str | None = None
    STATUS_DESCRIPTION: str | None = None

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

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None

    # System fields
    OPENED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    # Multi-field values (contact methods)
    PHONE: list[dict] | None = None
    EMAIL: list[dict] | None = None
    WEB: list[dict] | None = None
    IM: list[dict] | None = None
    LINK: list[dict] | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
