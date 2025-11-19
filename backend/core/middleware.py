"""
HTTP middleware for the application
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from backend.utils.logging import get_logger
import time

logger = get_logger(__name__)


async def request_logging_middleware(request: Request, call_next):
    """Enhanced request logging middleware to capture full request details for debugging"""
    start_time = time.time()
    
    # Log incoming request details
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = str(request.url.path)
    query_params = str(request.url.query) if request.url.query else ""
    
    # Capture all headers (sanitize sensitive ones)
    headers_dict = dict(request.headers)
    # Sanitize authorization header for logging
    if "authorization" in headers_dict:
        auth_header = headers_dict["authorization"]
        if auth_header.startswith("Bearer "):
            token_preview = auth_header[:20] + "..." if len(auth_header) > 20 else auth_header
            headers_dict["authorization"] = token_preview
    
    # Log request details
    logger.info(
        f"INCOMING REQUEST - Method: {method}, Path: {path}, "
        f"Query: {query_params}, Client IP: {client_ip}, "
        f"Forwarded-Proto: {request.headers.get('X-Forwarded-Proto', 'N/A')}, "
        f"Forwarded-Host: {request.headers.get('X-Forwarded-Host', 'N/A')}, "
        f"User-Agent: {request.headers.get('User-Agent', 'N/A')}"
    )
    logger.debug(f"Request headers: {headers_dict}")
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response details
        logger.info(
            f"REQUEST COMPLETE - Method: {method}, Path: {path}, "
            f"Status: {response.status_code}, Duration: {duration_ms:.2f}ms"
        )
        
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"REQUEST ERROR - Method: {method}, Path: {path}, "
            f"Error: {str(e)}, Duration: {duration_ms:.2f}ms",
            exc_info=True
        )
        raise


async def https_redirect_middleware(request: Request, call_next):
    """Handle HTTPS redirects and trailing slash issues when behind Traefik"""
    
    # Check if we're behind a proxy (Traefik)
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    forwarded_host = request.headers.get("X-Forwarded-Host")
    
    # If we're behind Traefik and the request is HTTP, redirect to HTTPS
    if forwarded_proto == "http" and forwarded_host:
        https_url = f"https://{forwarded_host}{request.url.path}"
        if request.url.query:
            https_url += f"?{request.url.query}"
        return RedirectResponse(url=https_url, status_code=301)
    
    # Handle trailing slash redirects to prevent 307 redirects
    # This helps with mixed content issues
    if request.url.path.endswith('/') and len(request.url.path) > 1:
        # Remove trailing slash and redirect
        new_path = request.url.path.rstrip('/')
        if request.url.query:
            new_url = f"{new_path}?{request.url.query}"
        else:
            new_url = new_path
        
        # Use the same protocol and host
        if forwarded_host:
            # Behind proxy - use forwarded host
            protocol = "https" if forwarded_proto == "https" else "http"
            redirect_url = f"{protocol}://{forwarded_host}{new_url}"
        else:
            # Direct access - use request URL
            redirect_url = f"{request.url.scheme}://{request.url.netloc}{new_url}"
        
        return RedirectResponse(url=redirect_url, status_code=301)
    
    response = await call_next(request)
    return response

