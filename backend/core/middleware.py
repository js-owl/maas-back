"""
HTTP middleware for the application
"""
from fastapi import Request
from fastapi.responses import RedirectResponse


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

