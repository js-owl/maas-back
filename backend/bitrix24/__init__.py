"""Bitrix24 REST API wrapper.

Provides HTTP client, DTOs, and CRUD services for Bitrix24 CRM entities
(deals, leads, contacts, invoices, products, statuses, categories, userfields, etc.).

Authentication:
- Webhook: base_url = https://{portal}/rest/{user_id}/{webhook_code}/
- OAuth: base_url = https://{portal}/rest/, pass access_token to client; client adds auth to body.

EntityTypeId (for crm.category.*, crm.item.*): all crm.enum.ownertype IDs (LEAD=1, DEAL=2, CONTACT=3, COMPANY=4, INVOICE=5, QUOTE=7, REQUISITE=8, SMART_INVOICE=31, SMART_DOCUMENT=36, SMART_B2E_DOC=39, DYNAMIC_156, DYNAMIC_177).
OwnerType (ownerType for product rows, activities, etc.): all crm.enum.ownertype SYMBOL_CODE_SHORT (L, D, C, CO, I, Q, RQ, SI, DO, SBD, T9c, Tb1).

Error handling: BitrixAPIError(code, description) on API errors (e.g. QUERY_LIMIT_EXCEEDED).
Set logging to DEBUG for request/response logging (auth redacted).
"""

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.constants import EntityTypeId, OwnerType
from backend.bitrix24.exceptions import BitrixAPIError
from backend.bitrix24.dto import dump_exclude_none, from_result
from backend.bitrix24.dto.deal import Deal, DealCreate, DealUpdate
from backend.bitrix24.dto.status import Status, StatusCreate, StatusUpdate
from backend.bitrix24.dto.category import Category, CategoryCreate, CategoryUpdate
from backend.bitrix24.dto.userfield import Userfield, UserfieldCreate, UserfieldUpdate
from backend.bitrix24.dto.product import Product, ProductCreate, ProductUpdate
from backend.bitrix24.dto.product_property import (
    ProductProperty,
    ProductPropertyCreate,
    ProductPropertyUpdate,
)
from backend.bitrix24.dto.product_property_enum import (
    ProductPropertyEnum,
    ProductPropertyEnumCreate,
    ProductPropertyEnumUpdate,
)
from backend.bitrix24.dto.product_row import ProductRow, ProductRowCreate, ProductRowUpdate
from backend.bitrix24.dto.invoice import Invoice, InvoiceCreate, InvoiceUpdate
from backend.bitrix24.dto.lead import Lead, LeadCreate, LeadUpdate
from backend.bitrix24.dto.contact import Contact, ContactCreate, ContactUpdate
from backend.bitrix24.services.deal import DealService
from backend.bitrix24.services.status import StatusService
from backend.bitrix24.services.category import CategoryService
from backend.bitrix24.services.userfield import UserfieldService
from backend.bitrix24.services.product import ProductService
from backend.bitrix24.services.product_property import ProductPropertyService
from backend.bitrix24.services.product_property_enum import ProductPropertyEnumService
from backend.bitrix24.services.product_row import ProductRowService
from backend.bitrix24.services.invoice import InvoiceService
from backend.bitrix24.services.lead import LeadService
from backend.bitrix24.services.contact import ContactService

__all__ = [
    "BitrixClient",
    "BitrixAPIError",
    "EntityTypeId",
    "OwnerType",
    "dump_exclude_none",
    "from_result",
    "Deal",
    "DealCreate",
    "DealUpdate",
    "DealService",
    "Status",
    "StatusCreate",
    "StatusUpdate",
    "StatusService",
    "Category",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryService",
    "Userfield",
    "UserfieldCreate",
    "UserfieldUpdate",
    "UserfieldService",
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "ProductService",
    "ProductProperty",
    "ProductPropertyCreate",
    "ProductPropertyUpdate",
    "ProductPropertyService",
    "ProductPropertyEnum",
    "ProductPropertyEnumCreate",
    "ProductPropertyEnumUpdate",
    "ProductPropertyEnumService",
    "ProductRow",
    "ProductRowCreate",
    "ProductRowUpdate",
    "ProductRowService",
    "Invoice",
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceService",
    "Lead",
    "LeadCreate",
    "LeadUpdate",
    "LeadService",
    "Contact",
    "ContactCreate",
    "ContactUpdate",
    "ContactService",
]
