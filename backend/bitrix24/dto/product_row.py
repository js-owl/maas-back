"""Product row DTOs for crm.item.productrow.* methods."""

from pydantic import BaseModel


class ProductRowCreate(BaseModel):
    """Fields for creating a product row (productId, quantity, price, etc.)."""

    # Required fields
    ownerId: int  # Immutable - can only be set on creation
    ownerType: str  # Immutable - can only be set on creation
    productId: int

    # Product information
    productName: str | None = None

    # Pricing
    price: float | None = None
    quantity: float | None = None

    # Discount
    discountTypeId: int | None = None
    discountRate: float | None = None
    discountSum: float | None = None

    # Tax
    taxRate: float | None = None
    taxIncluded: str | None = None

    # Measurement
    measureCode: int | None = None
    measureName: str | None = None

    # Other
    customized: str | None = None
    sort: int | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductRowUpdate(BaseModel):
    """Fields for updating a product row."""

    # Product information (ownerId and ownerType are immutable - cannot be updated)
    productId: int | None = None
    productName: str | None = None

    # Pricing
    price: float | None = None
    quantity: float | None = None

    # Discount
    discountTypeId: int | None = None
    discountRate: float | None = None
    discountSum: float | None = None

    # Tax
    taxRate: float | None = None
    taxIncluded: str | None = None

    # Measurement
    measureCode: int | None = None
    measureName: str | None = None

    # Other
    customized: str | None = None
    sort: int | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class ProductRow(BaseModel):
    """Product row entity."""

    # Read-only fields
    id: int | None = None
    priceExclusive: float | None = None
    priceNetto: float | None = None
    priceBrutto: float | None = None
    type: int | None = None
    storeId: int | None = None

    # Immutable fields
    ownerId: int | None = None  # Immutable - can only be set on creation
    ownerType: str | None = None  # Immutable - can only be set on creation

    # Product information
    productId: int | None = None
    productName: str | None = None

    # Pricing
    price: float | None = None
    quantity: float | None = None

    # Discount
    discountTypeId: int | None = None
    discountRate: float | None = None
    discountSum: float | None = None

    # Tax
    taxRate: float | None = None
    taxIncluded: str | None = None

    # Measurement
    measureCode: int | None = None
    measureName: str | None = None

    # Other
    customized: str | None = None
    sort: int | None = None

    model_config = {"extra": "allow", "populate_by_name": True}
