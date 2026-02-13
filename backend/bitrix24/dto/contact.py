"""Contact DTOs for crm.contact.* methods."""

from pydantic import BaseModel


class ContactCreate(BaseModel):
    """Fields for creating a contact (crm.contact.add)."""

    # Basic information
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    PHOTO: dict | None = None
    BIRTHDATE: str | None = None
    POST: str | None = None

    # Classification
    TYPE_ID: str | None = None
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None

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

    # System fields
    COMMENTS: str | None = None
    OPENED: str | None = None
    EXPORT: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Company relationships
    COMPANY_ID: int | None = None  # Deprecated
    COMPANY_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

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


class ContactUpdate(BaseModel):
    """Fields for updating a contact."""

    # Basic information
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    PHOTO: dict | None = None
    BIRTHDATE: str | None = None
    POST: str | None = None

    # Classification
    TYPE_ID: str | None = None
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None

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

    # System fields
    COMMENTS: str | None = None
    OPENED: str | None = None
    EXPORT: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Company relationships
    COMPANY_ID: int | None = None  # Deprecated
    COMPANY_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

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


class Contact(BaseModel):
    """Contact entity as returned by crm.contact.get / list."""

    # Read-only fields
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
    HONORIFIC: str | None = None
    NAME: str | None = None
    SECOND_NAME: str | None = None
    LAST_NAME: str | None = None
    PHOTO: dict | None = None
    BIRTHDATE: str | None = None
    POST: str | None = None

    # Classification
    TYPE_ID: str | None = None
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None

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

    # System fields
    COMMENTS: str | None = None
    OPENED: str | None = None
    EXPORT: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Company relationships
    COMPANY_ID: int | None = None  # Deprecated
    COMPANY_IDS: list[int] | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None
    ORIGIN_VERSION: str | None = None

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
