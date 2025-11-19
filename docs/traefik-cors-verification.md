# Traefik CORS Configuration Verification

## Verification Status: ✅ CONFIGURED CORRECTLY

Based on the Traefik configuration file provided, the CORS middleware is correctly configured to allow PUT requests.

## Configuration Details

From the Traefik dynamic configuration file (`/etc/traefik/`):

### CORS Middleware Configuration

```yaml
http:
  middlewares:
    cors:
      headers:
        accessControlAllowOriginList:
          - "https://maas.aeromax-group.ru"
          - "10.33.42.18"
          - "https://dcksv-maas-dev.int.kronshtadt.ru"
        accessControlAllowMethods:
          - "GET"
          - "POST"
          - "PUT"        # ✅ PUT method is explicitly allowed
          - "DELETE"
          - "OPTIONS"
        accessControlAllowHeaders:
          - "Authorization"    # ✅ Authorization header is allowed
          - "Content-Type"    # ✅ Content-Type header is allowed
          - "Accept"
        accessControlAllowCredentials: true
        addVaryHeader: true
```

## Verification Results

✅ **PUT Method**: Explicitly listed in `accessControlAllowMethods`  
✅ **Authorization Header**: Included in `accessControlAllowHeaders`  
✅ **Content-Type Header**: Included in `accessControlAllowHeaders`  
✅ **Credentials**: Allowed (`accessControlAllowCredentials: true`)  
✅ **Origins**: Production domain (`https://maas.aeromax-group.ru`) is in allowed list

## Docker Compose Configuration

The backend service in `docker-compose.prod.yml` correctly references the CORS middleware:

```yaml
labels:
  - "traefik.http.routers.lk-api-int.middlewares=strip-api-prefix@docker,cors@file"
```

The `cors@file` middleware is properly configured and applied to the router.

## Conclusion

**Traefik CORS configuration is NOT the cause of the 403 error.** The middleware correctly allows:
- PUT method
- Authorization header
- Content-Type header
- All required CORS headers

The 403 error is coming from **nginx** (version 1.28.0) before the request reaches Traefik, as confirmed by:
- Response body showing `nginx/1.28.0`
- FastAPI application returns 401 (not 403) for authentication failures
- Traefik CORS middleware is correctly configured

## Next Steps

The issue must be resolved at the nginx level. See `docs/nginx-configuration-requirements.md` for the required nginx configuration changes.


