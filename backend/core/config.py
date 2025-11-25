"""
Core configuration module
Centralizes environment variables and application settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# External Services
CALCULATOR_BASE_URL = os.getenv("CALCULATOR_BASE_URL", "http://localhost:7000")
STL_SERVER_URL = os.getenv("STL_SERVER_URL")  # Legacy, prefer CALCULATOR_BASE_URL

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/shop.db")

# Bitrix24
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
BITRIX_MAAS_FUNNEL_NAME = os.getenv("BITRIX_MAAS_FUNNEL_NAME", "MaaS")
BITRIX_MAAS_CATEGORY_ID = os.getenv("BITRIX_MAAS_CATEGORY_ID")  # Optional, auto-detected if not set

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_STREAM_PREFIX = os.getenv("REDIS_STREAM_PREFIX", "bitrix:")
BITRIX_WORKER_ENABLED = os.getenv("BITRIX_WORKER_ENABLED", "true").lower() == "true"

# File Storage
UPLOAD_DIR = "uploads/3d_models"
DOCUMENT_UPLOAD_DIR = "uploads/documents"
PREVIEW_DIR = "uploads/previews"

# Application
APP_VERSION = "3.2.0"
APP_TITLE = "Manufacturing Service API"

