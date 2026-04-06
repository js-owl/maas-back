"""
Manufacturing Service API v2.1.0
Modular FastAPI application with clean architecture
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from backend.core.config import (
    APP_TITLE,
    APP_VERSION,
    BITRIX24_ACCESS_TOKEN,
    BITRIX24_TIMEOUT,
    BITRIX24_WEBHOOK_URL,
    BITRIX_ENABLED,
    BITRIX_VERIFY_TLS,
    BITRIX_PRODUCT_IBLOCK_ID,
    CALCULATOR_BASE_URL,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ORIGINS,
)
from backend.core.redis import init_redis, close_redis
from backend.bitrix24.async_queue.process import (
    start_executor_process,
    start_reverse_sync_process,
    stop_executor_process,
    stop_reverse_sync_process,
)
from backend.bitrix24.client import BitrixClient
from backend.bitrix24.startup_sync import run_constant_entity_startup_sync
from backend.bitrix24.funnel_cache import sync_deal_funnels
from backend.bitrix24.services.my_company_startup import sync_my_company_startup
from backend.bitrix24.seed_constant_entities import seed_constant_entity_initial_data
from backend.bitrix24.user_sync import enqueue_missing_users_startup_sync
from backend.bitrix24.sync_payload.external_lists import fetch_list_values
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
from backend.database import (
    seed_admin, ensure_schema, 
    _env_json_dict, apply_admin_location_overrides,
    ensure_demo_files,
    AsyncSessionLocal
)
from sqlalchemy import select, func
from fastapi import Request
from backend.utils.logging import get_logger
import time
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

# Add request logging middleware (before other middleware to capture all requests)
from backend.core.middleware import request_logging_middleware
app.middleware("http")(request_logging_middleware)

# Add HTTPS redirect middleware
app.middleware("http")(https_redirect_middleware)

# CORS configuration from config
# Log CORS configuration for debugging
logger.info(f"CORS Configuration - Origins: {CORS_ORIGINS}, Credentials: {CORS_ALLOW_CREDENTIALS}, Methods: {CORS_ALLOW_METHODS}, Headers: {CORS_ALLOW_HEADERS}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
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
from backend.invoices.router import router as invoices_router
from backend.calculations.router import router as calculations_router
from backend.orders.router import router as orders_router
from backend.call_requests.router import router as call_requests_router
from backend.kits.router import router as kits_router
from backend.basket.router import router as basket_router

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)
app.include_router(documents_router)
app.include_router(invoices_router)
app.include_router(calculations_router)
app.include_router(orders_router)
app.include_router(call_requests_router)
app.include_router(kits_router)
app.include_router(basket_router)

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
            "base_url": CALCULATOR_BASE_URL,
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


async def auto_migrate_invoices_if_needed():
    """Automatically migrate invoices from documents table if needed"""
    try:
        async with AsyncSessionLocal() as db:
            # Check if there are invoices in documents table
            from backend import models
            result = await db.execute(
                select(func.count(models.DocumentStorage.id)).where(
                    models.DocumentStorage.document_category == "invoice"
                )
            )
            invoice_doc_count = result.scalar() or 0
            
            # Check if invoices table has any records
            result = await db.execute(
                select(func.count(models.InvoiceStorage.id))
            )
            invoice_count = result.scalar() or 0
            
            # If there are invoice documents but no invoices, run migration
            if invoice_doc_count > 0 and invoice_count == 0:
                logger.info(f"Found {invoice_doc_count} invoice documents to migrate, running automatic migration...")
                # Import and run migration function directly
                from backend.database import ensure_invoices_table
                from backend.invoices.service import create_invoice_from_file_path
                from backend.invoices.repository import get_invoice_by_filename
                from backend.documents.repository import get_documents_by_category
                from sqlalchemy import update
                import json
                
                # Ensure invoices table exists
                await ensure_invoices_table()
                
                # Get all documents currently categorized as 'invoice'
                invoice_documents = await get_documents_by_category(db, "invoice")
                
                if invoice_documents:
                    migrated_count = 0
                    order_updates = {}
                    
                    for doc in invoice_documents:
                        try:
                            # Check if an invoice with this filename already exists
                            existing_invoice = await get_invoice_by_filename(db, doc.filename)
                            
                            if existing_invoice:
                                logger.debug(f"Invoice for document {doc.id} already exists, skipping")
                                continue
                            
                            # Extract order_id from file_metadata
                            order_id = None
                            if doc.file_metadata:
                                try:
                                    metadata = json.loads(doc.file_metadata)
                                    order_id = metadata.get("order_id")
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            
                            if not order_id:
                                # Try to infer from filename
                                try:
                                    if "invoice_order_" in doc.filename:
                                        parts = doc.filename.split("invoice_order_")[1].split("_")
                                        order_id = int(parts[0])
                                except (ValueError, IndexError):
                                    pass
                            
                            if not order_id:
                                logger.warning(f"Could not determine order_id for document {doc.id}, skipping")
                                continue
                            
                            # Create new InvoiceStorage record
                            new_invoice = await create_invoice_from_file_path(
                                db=db,
                                file_path=doc.file_path,
                                order_id=order_id,
                                bitrix_document_id=None,
                                generated_at=doc.uploaded_at,
                                original_filename=doc.original_filename
                            )
                            
                            if new_invoice:
                                migrated_count += 1
                                if order_id not in order_updates:
                                    order_updates[order_id] = []
                                order_updates[order_id].append(new_invoice.id)
                        except Exception as e:
                            logger.error(f"Error migrating document {doc.id}: {e}", exc_info=True)
                            await db.rollback()
                            await db.begin()
                    
                    # Update orders' invoice_ids
                    for order_id, new_invoice_ids in order_updates.items():
                        order_result = await db.execute(
                            select(models.Order).where(models.Order.order_id == order_id)
                        )
                        order = order_result.scalar_one_or_none()
                        if order:
                            current_invoice_ids = []
                            if order.invoice_ids:
                                try:
                                    current_invoice_ids = json.loads(order.invoice_ids) if isinstance(order.invoice_ids, str) else order.invoice_ids
                                except (json.JSONDecodeError, TypeError):
                                    current_invoice_ids = []
                            
                            for inv_id in new_invoice_ids:
                                if inv_id not in current_invoice_ids:
                                    current_invoice_ids.append(inv_id)
                            
                            await db.execute(
                                update(models.Order)
                                .where(models.Order.order_id == order_id)
                                .values(invoice_ids=json.dumps(current_invoice_ids))
                            )
                            await db.commit()
                    
                    logger.info(f"Automatic invoice migration completed: {migrated_count} invoices migrated")
            elif invoice_doc_count > 0 and invoice_count > 0:
                logger.debug(f"Invoice migration check: {invoice_doc_count} documents in documents table, {invoice_count} invoices in invoices table (migration may be partial)")
            else:
                logger.debug(f"Invoice migration check: {invoice_doc_count} documents, {invoice_count} invoices (no migration needed)")
    except Exception as e:
        logger.warning(f"Could not check/run invoice migration: {e}", exc_info=True)
        # Don't fail startup if migration check fails


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    
    # Ensure all tables and columns exist (PostgreSQL-compatible, idempotent)
    await ensure_schema()
    overrides = _env_json_dict("ADMIN_LOCATION_OVERRIDES_JSON")
    await apply_admin_location_overrides(overrides)
    await ensure_demo_files()

    # Seed constant-entity tables with initial data from attribute_data_mapping (idempotent; runs when tables are empty)
    try:
        _list_values = await fetch_list_values()
    except Exception as e:
        logger.warning("Failed to fetch external list values for seed (will use static fallbacks): %s", e)
        _list_values = None
    try:
        async with AsyncSessionLocal() as db:
            await seed_constant_entity_initial_data(db, BITRIX_PRODUCT_IBLOCK_ID, list_values=_list_values)
    except Exception as e:
        logger.warning("Constant-entity initial data seed failed (non-fatal): %s", e)

    # Constant-entity startup sync (reconcile local rows with Bitrix24, store external IDs in mapping)
    if BITRIX_ENABLED and BITRIX24_WEBHOOK_URL:
        try:
            client = BitrixClient(
                base_url=BITRIX24_WEBHOOK_URL,
                access_token=BITRIX24_ACCESS_TOKEN,
                timeout=BITRIX24_TIMEOUT,
                verify_tls=BITRIX_VERIFY_TLS,
            )
            async with AsyncSessionLocal() as db:
                await run_constant_entity_startup_sync(db, client)
                # Pull current deal funnels (pipelines) and their stages for local cache
                await sync_deal_funnels(db, client)
                await sync_my_company_startup(db, client)
        except Exception as e:
            logger.warning("Constant-entity startup sync failed (non-fatal): %s", e)

    # Automatically migrate invoices from documents table if needed
    await auto_migrate_invoices_if_needed()
    
    # Seed admin user
    await seed_admin()

    # Initialize Redis connection pool
    await init_redis(app)

    # Backward-compatibility startup sync for existing users: enqueue only missing non-admin, non-cancelled users
    if BITRIX_ENABLED and BITRIX24_WEBHOOK_URL:
        try:
            async with AsyncSessionLocal() as db:
                await enqueue_missing_users_startup_sync(db, app.state.redis)
        except Exception as e:
            logger.warning("Startup user sync failed (non-fatal): %s", e, exc_info=True)

    # Start Bitrix24 executor process
    start_executor_process(app)

    # Start Bitrix24 reverse sync process (Bitrix24 → MaaS) when enabled
    start_reverse_sync_process(app)

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown application resources."""
    stop_reverse_sync_process(app)
    stop_executor_process(app)
    await close_redis(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
 