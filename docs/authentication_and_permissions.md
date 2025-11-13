# Authentication and Authorization Model

## User Types
1. **Anonymous** (not logged in)
2. **Registered User** (individual/legal)
3. **Admin User** (is_admin=true)

## Authentication Method
- **JWT tokens** via `Authorization: Bearer <token>`
- **Custom header extraction** (no OAuth2)
- **Token contains**: username, is_admin flag
- **JSON-based login** (no form data)

## Endpoints by Permission Level

### Public (No Auth Required)
- `POST /register` - User registration
- `POST /login` - User login
- `GET /health`, `/health/detailed` - System health
- `GET /` - Root endpoint with API info
- `GET /files/demo` - Demo 3D models for anonymous calculations
- `POST /calculate-price` - Price calculations (demo files only for anonymous)
- `GET /services`, `/materials`, `/coefficients`, `/locations` - Calculator service data

### Authenticated Users Only
- `POST /logout` - User logout
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
2. **Login**: `POST /login` with username/password → returns JWT token
3. **API Calls**: Include `Authorization: Bearer <token>` header
4. **Logout**: `POST /logout` (client removes token)

## Security Notes

- **Password hashing**: bcrypt with salt
- **JWT expiration**: Configurable (default 24 hours)
- **Token validation**: Custom header extraction with database lookup
- **File access**: Strict ownership validation
- **Admin privileges**: Full access to all resources

## Error Responses

- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Valid token but insufficient permissions
- **404 Not Found**: Resource doesn't exist or not owned by user
