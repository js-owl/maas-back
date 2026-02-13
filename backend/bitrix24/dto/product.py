"""Product DTOs for catalog.product.* methods."""

from typing import Any

from pydantic import BaseModel


class ProductCreate(BaseModel):
    """Fields for creating a product (catalog.product.add).
    Pass product properties via properties (e.g. PROPERTY_<id> or property codes).
    """

    # Required fields
    iblockId: int  # Immutable - can only be set on creation
    name: str

    # Basic information
    code: str | None = None
    xmlId: str | None = None
    active: str | None = None
    sort: int | None = None

    # Dates
    dateActiveFrom: str | None = None
    dateActiveTo: str | None = None
    dateCreate: str | None = None
    timestampX: str | None = None

    # Description and images
    previewText: str | None = None
    previewTextType: str | None = None
    detailText: str | None = None
    detailTextType: str | None = None
    previewPicture: dict | None = None
    detailPicture: dict | None = None

    # Catalog organization
    iblockSectionId: int | None = None

    # Inventory
    quantity: float | None = None
    quantityReserved: float | None = None
    quantityTrace: str | None = None
    canBuyZero: str | None = None
    subscribe: str | None = None

    # Measurements
    measure: int | None = None
    weight: float | None = None
    width: float | None = None
    length: float | None = None
    height: float | None = None

    # Pricing
    priceType: str | None = None
    purchasingPrice: str | None = None
    purchasingCurrency: str | None = None

    # Tax
    vatId: int | None = None
    vatIncluded: str | None = None

    # User tracking
    createdBy: int | None = None
    modifiedBy: int | None = None

    properties: dict[str, Any] | None = None
    model_config = {"extra": "allow", "populate_by_name": True}


class ProductUpdate(BaseModel):
    """Fields for updating a product.
    Pass product properties via properties (e.g. PROPERTY_<id> or property codes).
    """

    # Basic information (iblockId is immutable - cannot be updated)
    name: str | None = None
    code: str | None = None
    xmlId: str | None = None
    active: str | None = None
    sort: int | None = None

    # Dates
    dateActiveFrom: str | None = None
    dateActiveTo: str | None = None
    dateCreate: str | None = None
    timestampX: str | None = None

    # Description and images
    previewText: str | None = None
    previewTextType: str | None = None
    detailText: str | None = None
    detailTextType: str | None = None
    previewPicture: dict | None = None
    detailPicture: dict | None = None

    # Catalog organization
    iblockSectionId: int | None = None

    # Inventory
    quantity: float | None = None
    quantityReserved: float | None = None
    quantityTrace: str | None = None
    canBuyZero: str | None = None
    subscribe: str | None = None

    # Measurements
    measure: int | None = None
    weight: float | None = None
    width: float | None = None
    length: float | None = None
    height: float | None = None

    # Pricing
    priceType: str | None = None
    purchasingPrice: str | None = None
    purchasingCurrency: str | None = None

    # Tax
    vatId: int | None = None
    vatIncluded: str | None = None

    # User tracking
    createdBy: int | None = None
    modifiedBy: int | None = None

    properties: dict[str, Any] | None = None
    model_config = {"extra": "allow", "populate_by_name": True}


class Product(BaseModel):
    """Product entity as returned by catalog.product.get / list."""

    # Read-only fields
    id: int | None = None
    available: str | None = None
    bundle: str | None = None
    negativeAmountTrace: str | None = None
    type: int | None = None

    # Basic information
    iblockId: int | None = None  # Immutable - can only be set on creation
    name: str | None = None
    code: str | None = None
    xmlId: str | None = None
    active: str | None = None
    sort: int | None = None

    # Dates
    dateActiveFrom: str | None = None
    dateActiveTo: str | None = None
    dateCreate: str | None = None
    timestampX: str | None = None

    # Description and images
    previewText: str | None = None
    previewTextType: str | None = None
    detailText: str | None = None
    detailTextType: str | None = None
    previewPicture: dict | None = None
    detailPicture: dict | None = None

    # Catalog organization
    iblockSectionId: int | None = None

    # Inventory
    quantity: float | None = None
    quantityReserved: float | None = None
    quantityTrace: str | None = None
    canBuyZero: str | None = None
    subscribe: str | None = None

    # Measurements
    measure: int | None = None
    weight: float | None = None
    width: float | None = None
    length: float | None = None
    height: float | None = None

    # Pricing
    priceType: str | None = None
    purchasingPrice: str | None = None
    purchasingCurrency: str | None = None

    # Tax
    vatId: int | None = None
    vatIncluded: str | None = None

    # User tracking
    createdBy: int | None = None
    modifiedBy: int | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
