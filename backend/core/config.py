"""
Core configuration module
Centralizes environment variables and application settings
"""
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Core / API
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET", f"{SECRET_KEY}-refresh")
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES_SESSION = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES_SESSION", "720"))
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_PATH = os.getenv("REFRESH_COOKIE_PATH", "/")
REFRESH_COOKIE_DOMAIN = os.getenv("REFRESH_COOKIE_DOMAIN") or None
REFRESH_COOKIE_SECURE = os.getenv("REFRESH_COOKIE_SECURE", "true").lower() == "true"
REFRESH_COOKIE_SAMESITE = os.getenv("REFRESH_COOKIE_SAMESITE", "lax")
APP_VERSION = os.getenv("APP_VERSION", "3.2.0")
APP_TITLE = os.getenv("APP_TITLE", "Manufacturing Service API")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://maas_user:maas_local_pass@localhost:5432/maas_backend")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")

# Calculator service
CALCULATOR_BASE_URL = os.getenv("CALCULATOR_BASE_URL", "http://localhost:7000")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_POOL_MAX_CONNECTIONS = int(os.getenv("REDIS_POOL_MAX_CONNECTIONS", "10"))

# Bitrix24
BITRIX_ENABLED = os.getenv("BITRIX_ENABLED", "true").lower() == "true"
BITRIX24_WEBHOOK_URL = os.getenv("BITRIX24_WEBHOOK_URL", "https://dcksv-bitrix-t2-dev.int.kronshtadt.ru/rest/1/onxaismaxtz8i4r3/")
BITRIX24_ACCESS_TOKEN = os.getenv("BITRIX24_ACCESS_TOKEN")
BITRIX24_TIMEOUT = float(os.getenv("BITRIX24_TIMEOUT", "30"))
BITRIX_VERIFY_TLS = os.getenv("BITRIX_VERIFY_TLS", "false").lower() == "true"
# Product catalog: iblockId for ProductCreate (catalog.product.add).
# Source: config (env BITRIX_PRODUCT_IBLOCK_ID). Use one catalog for synced products; set in deployment to the target Bitrix iblock ID.
BITRIX_PRODUCT_IBLOCK_ID = int(os.getenv("BITRIX_PRODUCT_IBLOCK_ID", "14"))
# Reverse sync (Bitrix24 → MaaS): enable and run interval in seconds.
BITRIX_REVERSE_SYNC_ENABLED = os.getenv("BITRIX_REVERSE_SYNC_ENABLED", "true").lower() == "true"
BITRIX_REVERSE_SYNC_INTERVAL_SECONDS = int(os.getenv("BITRIX_REVERSE_SYNC_INTERVAL_SECONDS", "300"))

# CORS
_cors_origins_raw = os.getenv("CORS_ORIGINS", '["*"]')
_cors_methods_raw = os.getenv("CORS_ALLOW_METHODS", '["*"]')
_cors_headers_raw = os.getenv("CORS_ALLOW_HEADERS", '["*"]')
try:
    CORS_ORIGINS = json.loads(_cors_origins_raw)
    CORS_ALLOW_METHODS = json.loads(_cors_methods_raw)
    CORS_ALLOW_HEADERS = json.loads(_cors_headers_raw)
except json.JSONDecodeError:
    CORS_ORIGINS = ["*"]
    CORS_ALLOW_METHODS = ["*"]
    CORS_ALLOW_HEADERS = ["*"]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

# File / document storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/3d_models")
TEMP_DIR = os.getenv("TEMP_DIR", "uploads/temp")
PREVIEW_DIR = os.getenv("PREVIEW_DIR", "uploads/previews")
DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "uploads/documents")

# Specific locations to some users
ADMIN_LOCATION_OVERRIDES_JSON = os.getenv("ADMIN_LOCATION_OVERRIDES_JSON", '{"AODMZ": "location_2", "AOIKAR": "location_1", "KTSPECTR": "location_3", "diam-aero": "location_2"}')
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", None)
DEFAULT_BITRIX_CATEGORY_NAME = os.getenv("DEFAULT_BITRIX_CATEGORY_NAME", "MaaS")

# Bank detailes
MYCOMPANY_REQUISITES = {
    "BITRIX_MYCOMPANY_TITLE": "ООО «Аэромакс»",
    "BITRIX_MYCOMPANY_RQ_COMPANY_FULL_NAME": "Общество с ограниченной ответственностью «Аэромакс»",
    "BITRIX_MYCOMPANY_RQ_COMPANY_NAME": "ООО «Аэромакс»",
    "BITRIX_MYCOMPANY_EMAIL": "info@aeromax-group.ru",
    "BITRIX_MYCOMPANY_PHONE": "84959214242",
    "BITRIX_MYCOMPANY_RQ_INN": "7725347482",
    "BITRIX_MYCOMPANY_RQ_KPP": "770801001",
    "BITRIX_MYCOMPANY_BANK_NAME": "ПАО «МТС-Банк»",
    "BITRIX_MYCOMPANY_BIK": "044525232",
    "BITRIX_MYCOMPANY_ACCOUNT": "40702810800000025918",
    "BITRIX_MYCOMPANY_ADDRESS_STREET": "Милютинский пер.",
    "BITRIX_MYCOMPANY_ADDRESS_BUILDING": "13, стр. 1",
    "BITRIX_MYCOMPANY_ADDRESS_OFFICE": "помещ. 1, ком. 12",
    "BITRIX_MYCOMPANY_ADDRESS_CITY": "Москва",
    "BITRIX_MYCOMPANY_ADDRESS_POSTAL": "101000",
    "BITRIX_MYCOMPANY_ADDRESS_REGION": "Россия",
}