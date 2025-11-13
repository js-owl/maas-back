"""
Manufacturing Service API v2.1.0
Modular FastAPI application with clean architecture
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from backend.core.config import APP_TITLE, APP_VERSION
from backend.core.middleware import https_redirect_middleware
from backend.core.dependencies import get_db
from backend.core.exceptions import BaseAPIException
from backend.core.error_handlers import (
    base_api_exception_handler,
    request_validation_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import RequestValidationError
from backend.database import seed_admin, ensure_order_new_columns, AsyncSessionLocal
from fastapi import Request
from backend.utils.logging import get_logger
import os
import json

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Manufacturing Service API with modular architecture",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add OAuth2 security scheme for /docs authorization
security = HTTPBearer()
app.openapi_schema = None  # Clear cache to regenerate with security

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=APP_TITLE,
        version=APP_VERSION,
        description="Manufacturing Service API with modular architecture",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add security to all endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["get", "post", "put", "delete", "patch"]:
                if "security" not in openapi_schema["paths"][path][method]:
                    openapi_schema["paths"][path][method]["security"] = [{"HTTPBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add HTTPS redirect middleware
app.middleware("http")(https_redirect_middleware)

# CORS configuration from environment variables
cors_origins = os.getenv("CORS_ORIGINS", '["*"]')
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", '["*"]')
cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", '["*"]')

# Parse JSON strings from environment variables
try:
    cors_origins = json.loads(cors_origins)
    cors_allow_methods = json.loads(cors_allow_methods)
    cors_allow_headers = json.loads(cors_allow_headers)
except json.JSONDecodeError:
    # Fallback to default values if JSON parsing fails
    cors_origins = ["*"]
    cors_allow_methods = ["*"]
    cors_allow_headers = ["*"]

# Log CORS configuration for debugging
logger.info(f"CORS Configuration - Origins: {cors_origins}, Credentials: {cors_allow_credentials}, Methods: {cors_allow_methods}, Headers: {cors_allow_headers}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
    expose_headers=["*"],  # Expose all headers to frontend
    max_age=3600,  # Cache preflight response for 1 hour
)

# Per-request database session middleware to ensure single transaction lifecycle
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    async with AsyncSessionLocal() as session:
        request.state.db = session
        try:
            response = await call_next(request)
            await session.commit()
            return response
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Register global exception handlers
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(BaseAPIException, base_api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Import and register all routers
from backend.auth.router import router as auth_router
from backend.users.router import router as users_router
from backend.files.router import router as files_router
from backend.documents.router import router as documents_router
from backend.calculations.router import router as calculations_router
from backend.orders.router import router as orders_router
from backend.bitrix.router import router as bitrix_router
from backend.bitrix.webhook_router import router as bitrix_webhook_router
from backend.call_requests.router import router as call_requests_router

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)
app.include_router(documents_router)
app.include_router(calculations_router)
app.include_router(orders_router)
app.include_router(bitrix_router)
app.include_router(bitrix_webhook_router)
app.include_router(call_requests_router)

# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"{APP_TITLE} v{APP_VERSION}",
        "version": APP_VERSION,
        "docs": "/docs",
        "architecture": "modular",
        "endpoints": {
            "auth": "/login, /logout, /register",
            "users": "/profile, /users",
            "calculations": "/calculate-price, /services, /materials, /coefficients, /locations"
        }
    }


@app.get('/health', tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": APP_VERSION}


@app.get('/health/detailed', tags=["System"])
async def detailed_health_check():
    """Detailed health check with system information"""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "architecture": "modular",
        "modules": {
            "auth": "active",
            "users": "active", 
            "calculations": "active"
        },
        "calculator_service": {
            "base_url": os.getenv("CALCULATOR_BASE_URL", "http://localhost:7000"),
            "status": "configured"
        }
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    
    # Run database migrations
    await ensure_order_new_columns()
    
    # Seed admin user
    await seed_admin()
    
    logger.info("Application startup complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
 