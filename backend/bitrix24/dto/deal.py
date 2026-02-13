"""Deal DTOs for crm.deal.* methods."""

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class DealCreate(BaseModel):
    """Fields for creating a deal (crm.deal.add).
    Pass user-defined fields via userfields (e.g. UF_CRM_*).
    """

    # Basic information
    TITLE: str | None = None
    TYPE_ID: str | None = None
    CATEGORY_ID: int | None = None  # Immutable - can only be set on creation
    STAGE_ID: str | None = None

    # Deal characteristics
    IS_RECURRING: str | None = None
    IS_RETURN_CUSTOMER: str | None = None
    IS_REPEATED_APPROACH: str | None = None
    PROBABILITY: int | None = None

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None
    TAX_VALUE: float | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # Dates
    BEGINDATE: str | None = None
    CLOSEDATE: str | None = None

    # System fields
    OPENED: str | None = None
    CLOSED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Source tracking
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    ADDITIONAL_INFO: str | None = None
    LOCATION_ID: str | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    userfields: dict[str, Any] | None = None
    model_config = {"extra": "allow"}


class DealUpdate(BaseModel):
    """Fields for updating a deal (crm.deal.update).
    Pass user-defined fields via userfields (e.g. UF_CRM_*).
    """

    # Basic information
    TITLE: str | None = None
    TYPE_ID: str | None = None
    # CATEGORY_ID is immutable - cannot be updated after creation
    STAGE_ID: str | None = None

    # Deal characteristics
    IS_RECURRING: str | None = None
    IS_RETURN_CUSTOMER: str | None = None
    IS_REPEATED_APPROACH: str | None = None
    PROBABILITY: int | None = None

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None
    TAX_VALUE: float | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # Dates
    BEGINDATE: str | None = None
    CLOSEDATE: str | None = None

    # System fields
    OPENED: str | None = None
    CLOSED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Source tracking
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    ADDITIONAL_INFO: str | None = None
    LOCATION_ID: str | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    userfields: dict[str, Any] | None = None
    model_config = {"extra": "allow"}


class Deal(BaseModel):
    """Deal entity as returned by crm.deal.get / crm.deal.list."""

    # Read-only fields
    ID: int | None = None
    STAGE_SEMANTIC_ID: str | None = None
    IS_NEW: str | None = None
    QUOTE_ID: int | None = None
    CREATED_BY_ID: int | None = None
    MODIFY_BY_ID: int | None = None
    MOVED_BY_ID: int | None = None
    DATE_CREATE: str | None = None
    DATE_MODIFY: str | None = None
    MOVED_TIME: str | None = None
    LEAD_ID: int | None = None
    LAST_ACTIVITY_TIME: str | None = None
    LAST_ACTIVITY_BY: int | None = None

    # Basic information
    TITLE: str | None = None
    TYPE_ID: str | None = None
    CATEGORY_ID: int | None = None  # Immutable - can only be set on creation
    STAGE_ID: str | None = None

    # Deal characteristics
    IS_RECURRING: str | None = None
    IS_RETURN_CUSTOMER: str | None = None
    IS_REPEATED_APPROACH: str | None = None
    PROBABILITY: int | None = None

    # Financial information
    CURRENCY_ID: str | None = None
    OPPORTUNITY: float | None = None
    IS_MANUAL_OPPORTUNITY: str | None = None
    TAX_VALUE: float | None = None

    # Relationships
    COMPANY_ID: int | None = None
    CONTACT_ID: int | None = None  # Deprecated
    CONTACT_IDS: list[int] | None = None

    # Dates
    BEGINDATE: str | None = None
    CLOSEDATE: str | None = None

    # System fields
    OPENED: str | None = None
    CLOSED: str | None = None
    COMMENTS: str | None = None
    ASSIGNED_BY_ID: int | None = None

    # Source tracking
    SOURCE_ID: str | None = None
    SOURCE_DESCRIPTION: str | None = None
    ADDITIONAL_INFO: str | None = None
    LOCATION_ID: str | None = None

    # External source tracking
    ORIGINATOR_ID: str | None = None
    ORIGIN_ID: str | None = None

    # UTM tracking
    UTM_SOURCE: str | None = None
    UTM_MEDIUM: str | None = None
    UTM_CAMPAIGN: str | None = None
    UTM_CONTENT: str | None = None
    UTM_TERM: str | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}
