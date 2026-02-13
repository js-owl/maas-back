"""Shared constants for Bitrix24 API (entityTypeId, ownerType for universal methods).

See: https://apidocs.bitrix24.com/api-reference/crm/data-types.html#object_type
     https://apidocs.bitrix24.com/api-reference/crm/auxiliary/enum/crm-enum-owner-type.html

All values from crm.enum.ownertype. Dynamic-type IDs (e.g. 156, 177) may differ per portal.
"""

from enum import IntEnum, StrEnum


class EntityTypeId(IntEnum):
    """Entity type IDs for crm.category.*, crm.item.* (entityTypeId parameter).

    Values from crm.enum.ownertype: ID of the object type.
    """

    LEAD = 1
    DEAL = 2
    CONTACT = 3
    COMPANY = 4
    INVOICE = 5  # Invoice (old version)
    QUOTE = 7  # Estimate
    REQUISITE = 8
    SMART_INVOICE = 31
    SMART_DOCUMENT = 36
    SMART_B2E_DOC = 39
    DYNAMIC_156 = 156  # Purchase (portal-specific)
    DYNAMIC_177 = 177  # Equipment Purchase (portal-specific)


class OwnerType(StrEnum):
    """CRM owner type (ownerType parameter) for product rows, activities, and other CRM methods.

    Values from crm.enum.ownertype: SYMBOL_CODE_SHORT (short symbolic code).
    Use wherever the API expects ownerType (e.g. crm.item.productrow.set, crm.activity.*).
    """

    LEAD = "L"
    DEAL = "D"
    CONTACT = "C"
    COMPANY = "CO"
    INVOICE = "I"
    QUOTE = "Q"
    REQUISITE = "RQ"
    SMART_INVOICE = "SI"
    SMART_DOCUMENT = "DO"
    SMART_B2E_DOC = "SBD"
    DYNAMIC_156 = "T9c"  # Purchase (portal-specific)
    DYNAMIC_177 = "Tb1"  # Equipment Purchase (portal-specific)
