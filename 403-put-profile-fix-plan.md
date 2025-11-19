# Fix 403 Forbidden Error on PUT /api/v3/profile

## Root Cause Identified

**Nginx (version 1.28.0) is returning the 403 Forbidden error** before the request reaches Traefik or FastAPI. This is confirmed by:
- Response body shows `nginx/1.28.0` 
- FastAPI application returns 401 (not 403) for authentication failures
- Traefik CORS middleware is correctly configured (PUT method allowed)
- OPTIONS handlers exist for all endpoints including `/profile`

## Current Status

✅ **FastAPI**: OPTIONS handlers exist for `/profile` endpoints (lines 21-22 in `backend/users/router.py`)
✅ **Traefik**: CORS middleware allows PUT method and required headers (confirmed from Traefik config image)
❌ **Nginx**: Blocking PUT requests (user doesn't have access to nginx config)

## Required Nginx Configuration

The security team needs to update nginx configuration with:

### 1. Allow PUT Method
```nginx
location /api/v3/ {
    # Allow PUT method explicitly - remove any limit_except that blocks PUT
    limit_except GET POST PUT DELETE OPTIONS {
        deny all;
    }
}
```

### 2. Preserve Authorization Header
```nginx
location /api/v3/ {
    proxy_pass_request_headers on;
    proxy_set_header Authorization $http_authorization;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

### 3. Increase Request Body Size (if needed)
```nginx
client_max_body_size 10M;  # Adjust based on profile update payload size
```

### 4. Allow OPTIONS Preflight
```nginx
location /api/v3/ {
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        add_header 'Access-Control-Max-Age' 3600 always;
        return 204;
    }
}
```

## Implementation Steps

1. Create diagnostic endpoint to verify requests reach FastAPI
2. Add request logging middleware to capture full request details
3. Document nginx requirements for infrastructure team
4. Create test script to verify PUT requests work after nginx fix

## Todos

- [ ] Create /api/v3/debug/request endpoint to verify requests reach FastAPI and log all headers
- [ ] Add middleware to log all incoming requests with full headers before authentication
- [ ] Create nginx configuration documentation file with required settings for PUT requests
- [ ] Create test script to verify PUT requests work after nginx configuration update


