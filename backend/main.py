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
import time

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

# Add request logging middleware (before other middleware to capture all requests)
from backend.core.middleware import request_logging_middleware
app.middleware("http")(request_logging_middleware)

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


@app.api_route('/debug/request', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'], tags=["Debug"])
async def debug_request(request: Request):
    """
    Diagnostic endpoint to verify requests reach FastAPI application.
    Returns all request details including headers, method, path, and forwarded headers.
    Useful for debugging 403 errors from nginx/Traefik.
    """
    # Capture all headers
    headers_dict = {}
    for key, value in request.headers.items():
        # Sanitize authorization header for security
        if key.lower() == "authorization":
            if value.startswith("Bearer "):
                headers_dict[key] = value[:20] + "..." if len(value) > 20 else value
            else:
                headers_dict[key] = "***REDACTED***"
        else:
            headers_dict[key] = value
    
    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else None
    
    # Get forwarded headers (important for proxy debugging)
    forwarded_headers = {
        "X-Forwarded-Proto": request.headers.get("X-Forwarded-Proto", "N/A"),
        "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", "N/A"),
        "X-Forwarded-For": request.headers.get("X-Forwarded-For", "N/A"),
        "X-Real-IP": request.headers.get("X-Real-IP", "N/A"),
        "X-Forwarded-Port": request.headers.get("X-Forwarded-Port", "N/A"),
    }
    
    # Try to read request body if present (for POST/PUT requests)
    body_content = None
    try:
        if request.method in ['POST', 'PUT', 'PATCH']:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_content = json.loads(body_bytes.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    body_content = f"<binary or non-json content, length: {len(body_bytes)} bytes>"
    except Exception as e:
        body_content = f"<error reading body: {str(e)}>"
    
    response_data = {
        "status": "request_received",
        "message": "Request successfully reached FastAPI application",
        "request_details": {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "client": {
                "ip": client_ip,
                "port": client_port
            },
            "url": {
                "scheme": request.url.scheme,
                "netloc": request.url.netloc,
                "path": request.url.path,
                "query": request.url.query,
                "fragment": request.url.fragment
            },
            "forwarded_headers": forwarded_headers,
            "all_headers": headers_dict,
            "body": body_content
        },
        "proxy_detection": {
            "behind_proxy": bool(request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP")),
            "forwarded_proto": request.headers.get("X-Forwarded-Proto", "direct"),
            "forwarded_host": request.headers.get("X-Forwarded-Host", "direct")
        },
        "cors_info": {
            "origin": request.headers.get("Origin", "N/A"),
            "access_control_request_method": request.headers.get("Access-Control-Request-Method", "N/A"),
            "access_control_request_headers": request.headers.get("Access-Control-Request-Headers", "N/A")
        },
        "timestamp": time.time()
    }
    
    # Log the diagnostic request
    logger.info(f"DEBUG REQUEST - Method: {request.method}, Path: {request.url.path}, Client: {client_ip}")
    logger.debug(f"Debug request details: {json.dumps(response_data, indent=2, default=str)}")
    
    return response_data


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    
    # Run database migrations
    await ensure_order_new_columns()
    
    # Seed admin user
    await seed_admin()
    
    # Start Bitrix worker if enabled
    from backend.core.config import BITRIX_WORKER_ENABLED
    if BITRIX_WORKER_ENABLED:
        from backend.bitrix.worker import bitrix_worker
        import asyncio
        
        async def start_worker():
            """Start Bitrix worker in background"""
            try:
                logger.info("Starting Bitrix worker background task...")
                logger.info(f"About to call bitrix_worker.process_messages(), worker object: {bitrix_worker}")
                await bitrix_worker.process_messages()
                logger.info("bitrix_worker.process_messages() completed")
            except Exception as e:
                logger.error(f"Bitrix worker error: {e}", exc_info=True)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Start worker as background task
        task = asyncio.create_task(start_worker())
        logger.info(f"Bitrix worker task created: {task}")
        logger.info("Bitrix worker started in background")
    else:
        logger.info("Bitrix worker is disabled (BITRIX_WORKER_ENABLED=false)")
    
    logger.info("Application startup complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
 