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

# File Storage
UPLOAD_DIR = "uploads/3d_models"
DOCUMENT_UPLOAD_DIR = "uploads/documents"
PREVIEW_DIR = "uploads/previews"

# Application
APP_VERSION = "3.2.0"
APP_TITLE = "Manufacturing Service API"

