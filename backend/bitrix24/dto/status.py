"""Status DTOs for crm.status.* methods."""

from pydantic import BaseModel, Field


class StatusCreate(BaseModel):
    """Fields for creating a status (crm.status.add)."""

    # Required fields
    ENTITY_ID: str  # Immutable - entity type identifier
    STATUS_ID: str  # Immutable - status identifier
    NAME: str  # Status name

    # Optional immutable fields (can only be set on creation)
    CATEGORY_ID: int | None = None  # Immutable
    SEMANTICS: str | None = None  # Immutable - semantic type (e.g., "S" for success, "F" for failure)

    # Optional writable fields
    SORT: int | None = None
    COLOR: str | None = None
    EXTRA: dict | None = None  # Additional fields

    model_config = {"extra": "allow"}


class StatusUpdate(BaseModel):
    """Fields for updating a status (crm.status.update)."""

    # Writable fields (immutable fields ENTITY_ID, STATUS_ID, CATEGORY_ID, SEMANTICS excluded)
    NAME: str | None = None
    SORT: int | None = None
    COLOR: str | None = None
    EXTRA: dict | None = None  # Additional fields

    model_config = {"extra": "allow"}


class Status(BaseModel):
    """Status entity as returned by crm.status.list."""

    # Read-only fields
    ID: int | None = None
    NAME_INIT: str | None = None  # Default name
    SYSTEM: str | None = None  # System status flag

    # Immutable fields (can only be set on creation)
    ENTITY_ID: str | None = None  # Entity type identifier
    STATUS_ID: str | None = None  # Status identifier
    CATEGORY_ID: int | None = None  # Category/funnel ID
    SEMANTICS: str | None = None  # Semantic type (e.g., "S" for success, "F" for failure)

    # Writable fields
    NAME: str | None = None  # Status name
    SORT: int | None = None  # Sort order
    COLOR: str | None = None  # Display color
    EXTRA: dict | None = None  # Additional fields

    model_config = {"extra": "allow"}
