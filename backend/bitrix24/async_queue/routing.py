"""Routing table for Bitrix24 async queue processing."""
from typing import Any

from backend.bitrix24.dto.category import CategoryCreate, CategoryUpdate
from backend.bitrix24.dto.activity import ActivityCreate
from backend.bitrix24.dto.company import CompanyCreate, CompanyUpdate
from backend.bitrix24.dto.contact import ContactCreate, ContactUpdate
from backend.bitrix24.dto.deal import DealCreate, DealUpdate
from backend.bitrix24.dto.invoice import InvoiceCreate, InvoiceUpdate
from backend.bitrix24.dto.lead import LeadCreate, LeadUpdate
from backend.bitrix24.dto.product import ProductCreate, ProductUpdate
from backend.bitrix24.dto.product_property import (
    ProductPropertyCreate,
    ProductPropertyUpdate,
)
from backend.bitrix24.dto.product_property_enum import (
    ProductPropertyEnumCreate,
    ProductPropertyEnumUpdate,
)
from backend.bitrix24.dto.product_row import ProductRowCreate, ProductRowUpdate
from backend.bitrix24.dto.status import StatusCreate, StatusUpdate
from backend.bitrix24.dto.userfield import UserfieldCreate, UserfieldUpdate
from backend.bitrix24.services.activity import ActivityService
from backend.bitrix24.services.category import CategoryService
from backend.bitrix24.services.company import CompanyService
from backend.bitrix24.services.contact import ContactService
from backend.bitrix24.services.deal import DealService
from backend.bitrix24.services.invoice import InvoiceService
from backend.bitrix24.services.lead import LeadService
from backend.bitrix24.services.product import ProductService
from backend.bitrix24.services.product_property import ProductPropertyService
from backend.bitrix24.services.product_property_enum import ProductPropertyEnumService
from backend.bitrix24.services.product_row import ProductRowService
from backend.bitrix24.services.status import StatusService
from backend.bitrix24.services.userfield import UserfieldService

ActionMap = dict[str, str]
RoutingEntry = dict[str, Any]

ENTITY_TYPE_ROUTING: dict[str, RoutingEntry] = {
    "activity": {
        "service": ActivityService,
        "actions": {"create": "add"},
        # The processor resolves OWNER_ID before validating ActivityCreate.
        "dto": {"create": ActivityCreate},
    },
    "deal": {
        "service": DealService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": DealCreate, "update": DealUpdate},
    },
    "contact": {
        "service": ContactService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": ContactCreate, "update": ContactUpdate},
    },
    "company": {
        "service": CompanyService,
        "actions": {"create": "add", "update": "update"},
        "dto": {"create": CompanyCreate, "update": CompanyUpdate},
    },
    "lead": {
        "service": LeadService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": LeadCreate, "update": LeadUpdate},
    },
    "invoice": {
        "service": InvoiceService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": InvoiceCreate, "update": InvoiceUpdate},
    },
    "product": {
        "service": ProductService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": ProductCreate, "update": ProductUpdate},
    },
    "product_row": {
        "service": ProductRowService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": ProductRowCreate, "update": ProductRowUpdate},
        "requires": ["owner_type", "owner_id"],
    },
    "product_property": {
        "service": ProductPropertyService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": ProductPropertyCreate, "update": ProductPropertyUpdate},
    },
    "product_property_enum": {
        "service": ProductPropertyEnumService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": ProductPropertyEnumCreate, "update": ProductPropertyEnumUpdate},
    },
    "category": {
        "service": CategoryService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": CategoryCreate, "update": CategoryUpdate},
        "requires": ["entity_type_id"],
    },
    "status": {
        "service": StatusService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": StatusCreate, "update": StatusUpdate},
    },
    "userfield": {
        "service": UserfieldService,
        "actions": {"create": "add", "update": "update", "delete": "delete"},
        "dto": {"create": UserfieldCreate, "update": UserfieldUpdate},
        "requires": ["entity"],
    },
}


__all__ = ["ENTITY_TYPE_ROUTING"]
