"""Material enums used for Bitrix CRM field mapping and MATERIALS catalog keys."""

from enum import Enum


class MaterialNameMain(str, Enum):
    STEEL = "steel"
    NON_FERROUS = "non_ferrous"
    COMPOSITE = "composite"
    PLASTIC = "plastic"
    OTHER = "other"


class MaterialFamily(str, Enum):
    ALUMINIUM = "aluminium"
    BRONZE = "bronze"
    PLASTIC_3D = "plastic_3d"
    LATUN = "latun"
    CARBON = "carbon"
    STAINLESS = "stainless"
    COPPER = "copper"
    TITANIUM = "titanium"
    MAGNESIUM = "magnesium"
    NICKEL = "nickel"
    ZINC = "zinc"
    PCM = "pcm"
    OTHER = "other"


class MaterialGroup(str, Enum):
    STRUCT_STEEL = "struct_steel"
    TOOL_STEEL = "tool_steel"
    STRUCT_NON_FE = "struct_non_fe"
    CAST_ALLOY = "cast_alloy"
    SI_FABRICS = "si_fabrics"
    GLASS_FABRICS = "glass_fabrics"
    ROVING_FABRICS = "roving_fabrics"
    CARBON_FABRICS = "carbon_fabrics"
    QUARTZ_FABRICS = "quartz_fabrics"
    OTHER = "other"


class MaterialNameGroup(str, Enum):
    CORR_RESIST = "corr_resist"
    CREEP_RESIST = "creep_resist"
    SCALE_RESIST = "scale_resist"
    HOT_WORK = "hot_work"
    LOW_FRICTION = "low_friction"
    ELECTRO_STEEL = "electro_steel"
    MAGNETIC_STEEL = "magnetic_steel"
    HS_STEEL = "hs_steel"
    UHS_STEEL = "uhs_steel"
    WR_STEEL = "wr_steel"
    HIGH_PURITY = "high_purity"
    QAULITY = "quality"
    HIGH_QAULITY = "high_quality"
    SUPER_QAULITY = "super_quality"
    OTHER = "other"


class MaterialPriceUnits(str, Enum):
    KG = "kg"
    M = "m"
    M2 = "m2"


class MaterialForm(str, Enum):
    POWDER = "powder"
    SHEET = "sheet"
    ROD = "rod"
    HEXAGON = "hexagon"
    TEXTILE = "textile"
    PLATE = "plate"
    PREPREG = "pre-preg"
    THREAD = "thread"
    OTHER = "other"


class ServiceType(str, Enum):
    PRINTING = "printing"
    CNC_MILLING = "cnc-milling"
    COMPOSITE = "composite"
    ELECTROPLATING_AUTO = "electroplating_auto"


# Maps Bitrix primary material class → calculator applicable_processes
SERVICE_TYPE_BY_MATERIAL_MAIN: dict[MaterialNameMain, list[ServiceType]] = {
    MaterialNameMain.STEEL: [ServiceType.CNC_MILLING, ServiceType.ELECTROPLATING_AUTO],
    MaterialNameMain.NON_FERROUS: [ServiceType.CNC_MILLING, ServiceType.ELECTROPLATING_AUTO],
    MaterialNameMain.COMPOSITE: [ServiceType.COMPOSITE],
    MaterialNameMain.PLASTIC: [ServiceType.PRINTING],
    MaterialNameMain.OTHER: [],
}
