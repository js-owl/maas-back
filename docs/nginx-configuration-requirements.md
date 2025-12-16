# Nginx Configuration Requirements for PUT /api/v3/profile

## Problem

PUT requests to `/api/v3/profile` are returning `403 Forbidden` from nginx (version 1.28.0) before reaching Traefik or FastAPI. This document outlines the required nginx configuration to allow PUT requests and preserve necessary headers.

## Root Cause

Nginx security layer is blocking PUT requests before they reach the application. The 403 error is confirmed to be from nginx (response body shows `nginx/1.28.0`).

## Required Nginx Configuration

### 1. Allow PUT Method

The nginx configuration must explicitly allow PUT method. If using `limit_except`, ensure PUT is included:

```nginx
location /api/v3/ {
    # Option 1: Explicitly allow PUT in limit_except
    limit_except GET POST PUT DELETE OPTIONS {
        deny all;
    }
    
    # Option 2: If you need to restrict methods, ensure PUT is allowed
    # limit_except GET POST PUT {
    #     deny all;
    # }
    
    # Option 3: Remove limit_except entirely if all methods should be allowed
    # (Not recommended for production, but useful for debugging)
}
```

### 2. Preserve Authorization Header

The Authorization header must be passed through to the backend:

```nginx
location /api/v3/ {
    # Ensure headers are passed through
    proxy_pass_request_headers on;
    
    # Explicitly preserve Authorization header
    proxy_set_header Authorization $http_authorization;
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # Proxy to Traefik (adjust port/host as needed)
    proxy_pass http://traefik:80;
}
```

### 3. Increase Request Body Size (if needed)

If profile update payloads are large, increase the body size limit:

```nginx
http {
    # Set in http block or server block
    client_max_body_size 10M;  # Adjust based on actual payload size
    
    server {
        location /api/v3/ {
            # ... other configuration
        }
    }
}
```

### 4. Allow OPTIONS Preflight Requests

CORS preflight requests (OPTIONS) must be allowed:

```nginx
location /api/v3/ {
    # Handle OPTIONS preflight requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        add_header 'Access-Control-Max-Age' 3600 always;
        add_header 'Content-Type' 'text/plain; charset=utf-8' always;
        add_header 'Content-Length' 0 always;
        return 204;
    }
    
    # ... rest of configuration
}
```

### 5. Complete Example Configuration

Here's a complete nginx location block configuration:

```nginx
location /api/v3/ {
    # Allow all required HTTP methods
    limit_except GET POST PUT DELETE OPTIONS {
        deny all;
    }
    
    # Preserve all request headers
    proxy_pass_request_headers on;
    
    # Set proxy headers
    proxy_set_header Authorization $http_authorization;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    
    # Handle OPTIONS preflight
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        add_header 'Access-Control-Max-Age' 3600 always;
        add_header 'Content-Type' 'text/plain; charset=utf-8' always;
        add_header 'Content-Length' 0 always;
        return 204;
    }
    
    # Proxy settings
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    proxy_buffering off;
    
    # Proxy to Traefik (adjust as needed)
    proxy_pass http://traefik:80;
    
    # Error handling
    proxy_intercept_errors off;
}
```

## Verification Steps

After updating nginx configuration:

1. **Test OPTIONS preflight:**
   ```bash
   curl -X OPTIONS https://maas.aeromax-group.ru/api/v3/profile \
     -H "Origin: https://maas.aeromax-group.ru" \
     -H "Access-Control-Request-Method: PUT" \
     -H "Access-Control-Request-Headers: Authorization,Content-Type" \
     -v
   ```
   Should return `204 No Content` with appropriate CORS headers.

2. **Test PUT request:**
   ```bash
   curl -X PUT https://maas.aeromax-group.ru/api/v3/profile \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"full_name":"Test"}' \
     -v
   ```
   Should reach FastAPI (check backend logs) or return appropriate error from FastAPI, not 403 from nginx.

3. **Use diagnostic endpoint:**
   ```bash
   curl -X PUT https://maas.aeromax-group.ru/api/v3/debug/request \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"test":"data"}' \
     -v
   ```
   If this returns request details, the request reached FastAPI successfully.

## Common Issues

### Issue: Still getting 403 after configuration

**Check:**
- Nginx configuration syntax: `nginx -t`
- Nginx reloaded: `nginx -s reload` or `systemctl reload nginx`
- Check nginx error logs: `/var/log/nginx/error.log`
- Verify location block matches `/api/v3/` path
- Check if there are multiple location blocks that might conflict

### Issue: Authorization header missing

**Check:**
- `proxy_pass_request_headers on;` is set
- `proxy_set_header Authorization $http_authorization;` is present
- No other middleware is stripping the header

### Issue: Request body too large

**Check:**
- `client_max_body_size` is set appropriately
- Check nginx error logs for "client intended to send too large body" errors

## Testing with Diagnostic Endpoint

The application includes a diagnostic endpoint at `/api/v3/debug/request` that shows:
- All request headers (sanitized)
- Forwarded headers from proxy
- Request method, path, query parameters
- Request body (if present)
- Proxy detection information

Use this endpoint to verify:
1. Requests reach FastAPI (if you get a response, nginx/Traefik are passing requests)
2. Headers are preserved correctly
3. Forwarded headers are set properly

## Related Files

- `403-put-profile-fix-plan.md` - Root cause analysis and fix plan
- `backend/main.py` - Diagnostic endpoint implementation
- `backend/core/middleware.py` - Request logging middleware

## Notes

- The nginx configuration shown here is for the security layer before Traefik
- Traefik CORS middleware is already correctly configured (PUT method allowed)
- FastAPI application has OPTIONS handlers for all endpoints
- The issue is specifically with nginx blocking PUT requests before they reach Traefik




