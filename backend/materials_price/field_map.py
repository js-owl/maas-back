"""Bitrix CRM field requirements for materials and prices smart processes."""

from enum import Enum
from typing import Any

from backend.materials_price.enums import (
    MaterialFamily,
    MaterialForm,
    MaterialGroup,
    MaterialNameGroup,
    MaterialNameMain,
    MaterialPriceUnits,
)

# key = MATERIALS dict key
# value = bitrix_name / bitrix_type / bitrix_enum / is_multiple
M_REQ: dict[str, dict[str, Any]] = {
    "material_name_main": {
        "bitrix_name": "PrimaryName",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialNameMain.STEEL: "Сталь",
            MaterialNameMain.NON_FERROUS: "Цветные металлы",
            MaterialNameMain.COMPOSITE: "Композит",
            MaterialNameMain.PLASTIC: "Пластик",
            MaterialNameMain.OTHER: "Другое",
        },
        "is_multiple": "N",
    },
    "material_name": {
        "bitrix_name": "SecondaryName",
        "bitrix_type": "string",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
    "family": {
        "bitrix_name": "Family",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialFamily.ALUMINIUM: "алюминий",
            MaterialFamily.BRONZE: "бронза",
            MaterialFamily.PLASTIC_3D: "пластик для 3D-печати",
            MaterialFamily.LATUN: "латунь",
            MaterialFamily.CARBON: "углеродистая",
            MaterialFamily.STAINLESS: "легированная",
            MaterialFamily.COPPER: "медь",
            MaterialFamily.TITANIUM: "титан",
            MaterialFamily.MAGNESIUM: "магний",
            MaterialFamily.NICKEL: "никель",
            MaterialFamily.ZINC: "цинк",
            MaterialFamily.PCM: "полимерный композиционный материал",
            MaterialFamily.OTHER: "другое",
        },
        "is_multiple": "N",
    },
    "material_group": {
        "bitrix_name": "Group",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialGroup.STRUCT_STEEL: "конструкционная",
            MaterialGroup.TOOL_STEEL: "инструментальная",
            MaterialGroup.STRUCT_NON_FE: "деформируемый сплав",
            MaterialGroup.CAST_ALLOY: "литейный сплав",
            MaterialGroup.SI_FABRICS: "кремнеземная ткань",
            MaterialGroup.GLASS_FABRICS: "стеклянная ткань",
            MaterialGroup.ROVING_FABRICS: "ровинговая ткань",
            MaterialGroup.CARBON_FABRICS: "углеродная ткань",
            MaterialGroup.QUARTZ_FABRICS: "кварцевая ткань",
            MaterialGroup.OTHER: "другое",
        },
        "is_multiple": "N",
    },
    "material_name_group": {
        "bitrix_name": "Subgroup",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialNameGroup.CORR_RESIST: "коррозионно-стойкая",
            MaterialNameGroup.CREEP_RESIST: "жаропрочная",
            MaterialNameGroup.SCALE_RESIST: "жаростойкая",
            MaterialNameGroup.HOT_WORK: "теплостойкая",
            MaterialNameGroup.LOW_FRICTION: "антифрикционная",
            MaterialNameGroup.ELECTRO_STEEL: "электротехническая",
            MaterialNameGroup.MAGNETIC_STEEL: "магнитная",
            MaterialNameGroup.HS_STEEL: "высокопрочная",
            MaterialNameGroup.UHS_STEEL: "сверхпрочная",
            MaterialNameGroup.WR_STEEL: "износостойкая",
            MaterialNameGroup.HIGH_PURITY: "высокочистый",
            MaterialNameGroup.QAULITY: "качественная",
            MaterialNameGroup.HIGH_QAULITY: "высококачественная",
            MaterialNameGroup.SUPER_QAULITY: "особо качественная",
            MaterialNameGroup.OTHER: "другое",
        },
        "is_multiple": "Y",
    },
    "density": {
        "bitrix_name": "Density",
        "bitrix_type": "double",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
    "minimum_order_quantity": {
        "bitrix_name": "MinOrder",
        "bitrix_type": "double",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
    "price_units": {
        "bitrix_name": "PriceUnits",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialPriceUnits.KG: "кг",
            MaterialPriceUnits.M: "м",
            MaterialPriceUnits.M2: "м2",
        },
        "is_multiple": "Y",
    },
    "one_layer_thickness": {
        "bitrix_name": "OneLayerThickness",
        "bitrix_type": "double",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
}

P_REQ: dict[str, dict[str, Any]] = {
    "forms": {
        "bitrix_name": "SemiFinished",
        "bitrix_type": "enumeration",
        "bitrix_enum": {
            MaterialForm.POWDER: "порошок",
            MaterialForm.SHEET: "лист",
            MaterialForm.ROD: "пруток",
            MaterialForm.HEXAGON: "шестигранник",
            MaterialForm.TEXTILE: "ткань",
            MaterialForm.PLATE: "плита",
            MaterialForm.PREPREG: "препрег",
            MaterialForm.THREAD: "нить",
            MaterialForm.OTHER: "другое",
        },
        "is_multiple": "N",
    },
    "price": {
        "bitrix_name": "ManualPrice",
        "bitrix_type": "money",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
    "auto_price": {
        "bitrix_name": "AutoPrice",
        "bitrix_type": "money",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
    "parent": {
        "bitrix_name": "Parent",
        "bitrix_type": "crm",
        "bitrix_enum": {},
        "is_multiple": "N",
    },
}


def enum_text_to_member(req_key: str, text: str) -> Enum | None:
    """Resolve Bitrix enum display text to our Enum member (case-insensitive)."""
    req = (M_REQ | P_REQ).get(req_key) or {}
    mapping: dict[Enum, str] = req.get("bitrix_enum") or {}
    needle = text.casefold()
    for member, label in mapping.items():
        if str(label).casefold() == needle:
            return member
    return None
