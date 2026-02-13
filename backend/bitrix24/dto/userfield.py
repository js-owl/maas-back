"""Userfield DTOs for crm.{entity}.userfield.* methods."""

from typing import Any

from pydantic import BaseModel


class UserfieldCreate(BaseModel):
    """Fields for creating a userfield (FIELD_NAME, USER_TYPE_ID, LABEL, etc.)."""

    # Required immutable fields (can only be set on creation)
    ENTITY_ID: str  # Entity type (e.g., "CRM_DEAL", "CRM_CONTACT")
    FIELD_NAME: str  # Field code (must start with UF_CRM_)
    USER_TYPE_ID: str  # Data type (string, integer, double, datetime, boolean, file, etc.)

    # Optional immutable fields
    XML_ID: str | None = None  # External ID

    # Field settings
    SORT: int | None = None  # Sort order
    MULTIPLE: str | None = None  # Multiple values flag (Y/N)
    MANDATORY: str | None = None  # Required flag (Y/N)

    # Display settings
    SHOW_FILTER: str | None = None  # Show in list filter (Y/N)
    SHOW_IN_LIST: str | None = None  # Show in list (Y/N)
    EDIT_IN_LIST: str | None = None  # Allow user editing (Y/N)
    IS_SEARCHABLE: str | None = None  # Field values participate in search (Y/N)

    # Labels (locale-keyed: e.g. {"ru": "…", "en": "…"})
    LABEL: str | None = None  # Field display name
    EDIT_FORM_LABEL: dict[str, str] | None = None  # Label in edit form
    LIST_COLUMN_LABEL: dict[str, str] | None = None  # Header in list
    LIST_FILTER_LABEL: dict[str, str] | None = None  # Filter label in list

    # Messages (locale-keyed)
    ERROR_MESSAGE: dict[str, str] | None = None  # Error message
    HELP_MESSAGE: dict[str, str] | None = None  # Help text

    # List elements (for list/enum type fields)
    LIST: list[dict[str, Any]] | None = None  # List elements with ID, SORT, VALUE, DEF, DEL

    # Additional settings
    SETTINGS: dict[str, Any] | None = None  # Additional settings (depend on type)

    model_config = {"extra": "allow"}


class UserfieldUpdate(BaseModel):
    """Fields for updating a userfield."""

    # Immutable fields (ENTITY_ID, FIELD_NAME, USER_TYPE_ID) excluded - cannot be updated

    # Optional writable fields
    XML_ID: str | None = None

    # Field settings
    SORT: int | None = None
    MULTIPLE: str | None = None
    MANDATORY: str | None = None

    # Display settings
    SHOW_FILTER: str | None = None
    SHOW_IN_LIST: str | None = None
    EDIT_IN_LIST: str | None = None
    IS_SEARCHABLE: str | None = None

    # Labels (locale-keyed: e.g. {"ru": "…", "en": "…"})
    LABEL: str | None = None  # Field display name
    EDIT_FORM_LABEL: dict[str, str] | None = None
    LIST_COLUMN_LABEL: dict[str, str] | None = None
    LIST_FILTER_LABEL: dict[str, str] | None = None

    # Messages (locale-keyed)
    ERROR_MESSAGE: dict[str, str] | None = None
    HELP_MESSAGE: dict[str, str] | None = None

    # List elements (for list/enum type fields)
    LIST: list[dict[str, Any]] | None = None

    # Additional settings
    SETTINGS: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class Userfield(BaseModel):
    """Userfield entity as returned by userfield.get / list."""

    # Read-only fields
    ID: int | None = None

    # Immutable fields (can only be set on creation)
    ENTITY_ID: str | None = None  # Entity type
    FIELD_NAME: str | None = None  # Field code
    USER_TYPE_ID: str | None = None  # Data type

    # Writable fields
    XML_ID: str | None = None

    # Field settings
    SORT: int | None = None
    MULTIPLE: str | None = None
    MANDATORY: str | None = None

    # Display settings
    SHOW_FILTER: str | None = None
    SHOW_IN_LIST: str | None = None
    EDIT_IN_LIST: str | None = None
    IS_SEARCHABLE: str | None = None

    # Labels (locale-keyed: e.g. {"ru": "…", "en": "…"})
    LABEL: str | None = None  # Field display name
    EDIT_FORM_LABEL: dict[str, str] | None = None
    LIST_COLUMN_LABEL: dict[str, str] | None = None
    LIST_FILTER_LABEL: dict[str, str] | None = None

    # Messages (locale-keyed)
    ERROR_MESSAGE: dict[str, str] | None = None
    HELP_MESSAGE: dict[str, str] | None = None

    # List elements (for list/enum type fields)
    LIST: list[dict[str, Any]] | None = None

    # Additional settings
    SETTINGS: dict[str, Any] | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
