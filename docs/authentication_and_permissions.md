# Authentication and Authorization Model

## User Types
1. **Anonymous** (not logged in)
2. **Registered User** (individual/legal)
3. **Admin User** (is_admin=true)

## Authentication Method
- **Access JWT** via `Authorization: Bearer <token>` for protected API calls.
- **Refresh JWT** is stored server-side in Redis by `jti` and sent only as an `HttpOnly` refresh cookie.
- **JSON-based login** (no form data) with `username`, `password`, and optional `remember_me`.
- **Custom header extraction** for access tokens (no OAuth2).
- **Access token contains**: username, is_admin flag, token type, issue time, and expiration.

## Endpoints by Permission Level

### Public (No Auth Required)
- `POST /register` - User registration
- `POST /login` - User login; returns access token and sets refresh cookie
- `POST /refresh` - Cookie-based access token refresh with rotation
- `POST /logout` - Clears refresh cookie and invalidates the refresh session when present
- `GET /health`, `/health/detailed` - System health
- `GET /` - Root endpoint with API info
- `GET /files/demo` - Demo 3D models for anonymous calculations
- `POST /calculate-price` - Price calculations (demo files only for anonymous)
- `GET /services`, `/materials`, `/coefficients`, `/locations` - Calculator service data

### Authenticated Users Only
- `GET /profile`, `PUT /profile` - User profile management
- `POST /files` - Upload 3D models (with preview generation)
- `POST /documents` - Upload documents (simple storage)
- `GET /files` - List own files
- `GET /files/{id}` - Access own files or demo files
- `POST /calculate-price` - Price calculations (own files + demo files)
- `POST /orders` - Create orders
- `GET /orders` - List own orders
- `GET /orders/{id}` - Access own orders only

### Admin Only
- `GET /users` - List all users
- `GET /users/{id}`, `PUT /users/{id}`, `DELETE /users/{id}` - User management
- `GET /admin/orders` - List all orders
- `GET /admin/bitrix/*` - Bitrix sync operations
- **Access to all files/orders** regardless of owner

## File Access Rules

### Demo Files (IDs 1-5 or is_demo=true)
- **Anonymous**: calculation only
- **Authenticated**: calculation + download
- **Admin**: full access

### User-Uploaded Files
- **Owner**: full access
- **Admin**: full access
- **Others**: no access

## Special Cases

### `/calculate-price` - Optional Authentication
- **Anonymous**: demo files only
- **Authenticated**: own files + demo files
- **Admin**: all files

### File Upload Endpoints
- **`POST /files`**: 3D models with preview generation, file analysis (STP/STEP)
- **`POST /documents`**: PDFs, specs, manuals - simple storage, no processing

## Authentication Flow

1. **Registration**: `POST /register` with user data
2. **Login**: `POST /login` with `username`, `password`, and optional `remember_me`
3. **Login response**: JSON body returns a short-lived access token; `Set-Cookie` stores the refresh token as `HttpOnly`
4. **API calls**: Include `Authorization: Bearer <access_token>` for protected endpoints
5. **Refresh**: `POST /refresh` reads only the refresh cookie, verifies JWT + Redis session, rotates the refresh token, returns a new access token, and sets a new refresh cookie
6. **Logout**: `POST /logout` deletes the Redis refresh session when identifiable and clears the refresh cookie; access tokens naturally expire shortly after logout

## Access and Refresh Lifecycle

- **Access token**: Short-lived JWT (default 15 minutes) returned in response JSON and used only in the `Authorization` header.
- **Refresh token**: Signed JWT with a unique `jti`, stored in Redis as `auth:refresh:{jti}`, and sent only in the refresh cookie.
- **Rotation**: Every successful refresh deletes the old Redis entry and issues a new refresh token, new Redis entry, and new cookie.
- **Reuse protection**: A previously rotated or logged-out refresh token is rejected because its Redis entry is gone.

## Cookie Strategy and Remember Me

- Refresh cookie is `HttpOnly` so JavaScript cannot read it.
- Refresh cookie uses configurable `Secure` and `SameSite`; production should use HTTPS and explicit CORS origins.
- `remember_me=false` or omitted: browser session cookie with no persistent `Max-Age`; Redis/JWT still enforce a configurable server-side maximum.
- `remember_me=true`: persistent refresh cookie and Redis/JWT lifetime default to 30 days.
- Browser clients must send credentialed requests for login, refresh, and logout, for example `fetch(url, { credentials: "include" })`.

## Security Notes

- **Password hashing**: bcrypt with salt
- **JWT expiration**: Access tokens are short-lived; refresh lifetimes are configurable
- **Server-side refresh invalidation**: Redis allowlist with per-session `jti`
- **Refresh token rotation**: Refresh tokens are one-time use after successful rotation
- **Cookie protection**: Refresh token is not exposed in JSON or JavaScript-accessible storage
- **Token validation**: Custom header extraction with database lookup
- **File access**: Strict ownership validation
- **Admin privileges**: Full access to all resources

## Error Responses

- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Valid token but insufficient permissions
- **404 Not Found**: Resource doesn't exist or not owned by user
