"""Category (sales funnel) DTOs for crm.category.* methods."""

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    """Fields for creating a category (crm.category.add). API uses lowercase: name, sort, isDefault."""

    # Required field
    entityTypeId: int  # Required to specify which entity type this category belongs to

    # Basic information
    name: str | None = None
    sort: int | None = None

    # External source tracking
    originId: str | None = None
    originatorId: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class CategoryUpdate(BaseModel):
    """Fields for updating a category (crm.category.update)."""

    # Basic information (entityTypeId is read-only - cannot be updated)
    name: str | None = None
    sort: int | None = None

    # External source tracking
    originId: str | None = None
    originatorId: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class Category(BaseModel):
    """Category entity as returned by crm.category.get / list."""

    # Read-only fields
    id: int | None = None
    entityTypeId: int | None = None
    isDefault: bool | None = None

    # Basic information
    name: str | None = None
    sort: int | None = None

    # External source tracking
    originId: str | None = None
    originatorId: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
