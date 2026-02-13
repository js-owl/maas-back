"""Product property enum DTOs for catalog.productPropertyEnum.* methods."""

from pydantic import BaseModel, Field


class ProductPropertyEnumCreate(BaseModel):
    """Fields for creating a product property enum value."""

    # Required fields
    propertyId: int  # Product property ID this enum belongs to
    value: str  # Enum value text
    xmlId: str  # External ID

    # Optional fields
    def_: str | None = Field(None, alias="def")  # Default flag (use Field to handle 'def' keyword)
    sort: int | None = None  # Sort order

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductPropertyEnumUpdate(BaseModel):
    """Fields for updating a product property enum value."""

    # All fields optional for updates
    propertyId: int | None = None
    value: str | None = None
    xmlId: str | None = None
    def_: str | None = Field(None, alias="def")  # Default flag
    sort: int | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductPropertyEnum(BaseModel):
    """Product property enum entity."""

    # Read-only fields
    id: int | None = None

    # Basic information
    propertyId: int | None = None  # Product property ID this enum belongs to
    value: str | None = None  # Enum value text
    xmlId: str | None = None  # External ID
    def_: str | None = Field(None, alias="def")  # Default flag (Y/N)
    sort: int | None = None  # Sort order

    model_config = {"extra": "allow", "populate_by_name": True}
