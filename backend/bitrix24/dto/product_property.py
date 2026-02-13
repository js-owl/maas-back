"""Product property DTOs for catalog.productProperty.* methods."""

from pydantic import BaseModel


class ProductPropertyCreate(BaseModel):
    """Fields for creating a product property."""

    # Required fields
    iblockId: int  # Information block ID
    name: str  # Property name
    propertyType: str  # Property type (S=string, N=number, L=list, F=file, etc.)

    # Basic settings
    code: str | None = None  # Symbolic code
    xmlId: str | None = None  # External ID
    active: str | None = None  # Active flag
    sort: int | None = None  # Sort order

    # Property settings
    isRequired: str | None = None  # Required flag
    multiple: str | None = None  # Multiple values flag
    multipleCnt: int | None = None  # Multiple count
    withDescription: str | None = None  # With description flag

    # Display settings
    hint: str | None = None  # Hint text
    rowCount: int | None = None  # Row count for textarea
    colCount: int | None = None  # Column count for textarea

    # Search and filter
    searchable: str | None = None  # Searchable flag
    filtrable: str | None = None  # Filterable flag

    # Default value
    defaultValue: str | None = None  # Default value

    # List type settings
    listType: str | None = None  # List type (L=list, C=checkbox)

    # Link settings
    linkIblockId: int | None = None  # Linked information block ID

    # File settings
    fileType: str | None = None  # File type restrictions

    # User type
    userType: str | None = None  # User type
    userTypeSettings: dict | None = None  # User type settings

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductPropertyUpdate(BaseModel):
    """Fields for updating a product property."""

    # Basic information (all optional for updates)
    iblockId: int | None = None
    name: str | None = None
    propertyType: str | None = None

    # Basic settings
    code: str | None = None
    xmlId: str | None = None
    active: str | None = None
    sort: int | None = None

    # Property settings
    isRequired: str | None = None
    multiple: str | None = None
    multipleCnt: int | None = None
    withDescription: str | None = None

    # Display settings
    hint: str | None = None
    rowCount: int | None = None
    colCount: int | None = None

    # Search and filter
    searchable: str | None = None
    filtrable: str | None = None

    # Default value
    defaultValue: str | None = None

    # List type settings
    listType: str | None = None

    # Link settings
    linkIblockId: int | None = None

    # File settings
    fileType: str | None = None

    # User type
    userType: str | None = None
    userTypeSettings: dict | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductProperty(BaseModel):
    """Product property entity."""

    # Read-only fields
    id: int | None = None
    timestampX: str | None = None  # Last modification timestamp

    # Basic information
    iblockId: int | None = None
    name: str | None = None
    propertyType: str | None = None

    # Basic settings
    code: str | None = None
    xmlId: str | None = None
    active: str | None = None
    sort: int | None = None

    # Property settings
    isRequired: str | None = None
    multiple: str | None = None
    multipleCnt: int | None = None
    withDescription: str | None = None

    # Display settings
    hint: str | None = None
    rowCount: int | None = None
    colCount: int | None = None

    # Search and filter
    searchable: str | None = None
    filtrable: str | None = None

    # Default value
    defaultValue: str | None = None

    # List type settings
    listType: str | None = None

    # Link settings
    linkIblockId: int | None = None

    # File settings
    fileType: str | None = None

    # User type
    userType: str | None = None
    userTypeSettings: dict | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
