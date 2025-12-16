# Development Guide - Manufacturing Service Backend

This document provides comprehensive technical details for developers working on the Manufacturing Service Backend.

## 🏗️ Architecture Deep Dive

### Modular Design Principles

The backend follows a **feature-based modular architecture** where each business domain is encapsulated in its own module. This design promotes:

- **Separation of Concerns** - Each module handles one specific business domain
- **Maintainability** - Easy to locate and modify specific functionality
- **Testability** - Each module can be tested independently
- **Scalability** - New features can be added as separate modules
- **Code Reuse** - Shared logic extracted into services and utilities

### Module Structure Pattern

Each module follows the **Repository → Service → Router** pattern:

```
backend/{module}/
├── router.py      # FastAPI endpoints and request/response handling
├── service.py     # Business logic and orchestration
├── repository.py  # Database operations and data access
└── __init__.py    # Module initialization
```

### Core Modules

#### 1. **Core Module** (`backend/core/`)
- **Purpose**: Shared configuration, dependencies, and base classes
- **Key Files**:
  - `config.py` - Environment configuration and settings
  - `dependencies.py` - FastAPI dependency injection
  - `exceptions.py` - Custom exception classes
  - `error_handlers.py` - Global exception handlers
  - `base_repository.py` - Generic repository base class
  - `middleware.py` - Custom middleware components

#### 2. **Authentication Module** (`backend/auth/`)
- **Purpose**: JWT-based authentication and authorization
- **Key Features**:
  - Token generation and validation
  - Password hashing with bcrypt
  - Role-based access control (admin/user)
  - Session management

#### 3. **Users Module** (`backend/users/`)
- **Purpose**: User profile and account management
- **Key Features**:
  - User registration and profile management
  - Individual vs. legal entity user types
  - Conditional field validation
  - Admin user management

#### 4. **Files Module** (`backend/files/`)
- **Purpose**: 3D model file handling and storage
- **Key Features**:
  - File upload with base64 encoding
  - STL/STP file support
  - Automatic preview generation
  - File access control and permissions
  - Demo file management

#### 5. **Documents Module** (`backend/documents/`)
- **Purpose**: Document storage and management
- **Key Features**:
  - PDF, TXT, PPTX document support
  - Order document attachments
  - File metadata tracking
  - Access control

#### 6. **Calculations Module** (`backend/calculations/`)
- **Purpose**: Calculator service integration and price calculations
- **Key Features**:
  - External calculator service proxy
  - Anonymous price calculations
  - File-based parameter extraction
  - Error proxying from calculator service

#### 7. **Orders Module** (`backend/orders/`)
- **Purpose**: Order management and processing
- **Key Features**:
  - Order creation and lifecycle management
  - Document attachments
  - Status tracking
  - Bitrix CRM integration
  - Invoice management

#### 8. **Bitrix Module** (`backend/bitrix/`)
- **Purpose**: Bitrix24 CRM integration
- **Key Features**:
  - Deal and contact creation
  - Lead management
  - Sync queue with retry logic
  - Webhook handling
  - Invoice download

#### 9. **Call Requests Module** (`backend/call_requests/`)
- **Purpose**: Call request and lead management
- **Key Features**:
  - Lead capture and management
  - Bitrix lead creation
  - Contact information handling
  - Request tracking

## 🗄️ Database Layer

### Current Database: SQLite

**Connection**: `sqlite+aiosqlite:///./data/shop.db`

**Key Tables**:
- `users` - User accounts and profiles
- `files` - 3D model files and metadata
- `documents` - Document files and metadata
- `orders` - Manufacturing orders
- `order_documents` - Order-document relationships
- `call_requests` - Lead capture requests
- `bitrix_sync_queue` - CRM synchronization queue

### Database Models

All models are defined in `backend/models.py` using SQLAlchemy with async support:

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    user_type = Column(String, default="individual")  # individual/legal
    # ... additional fields
```

### Repository Pattern

Each module implements a repository class that inherits from `BaseRepository`:

```python
class UserRepository(BaseRepository[User]):
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
```

## 🔌 External Services Integration

### Calculator Service Integration

**Service URL**: `http://localhost:7000`

**Integration Pattern**:
- **Proxy Architecture** - Backend acts as transparent proxy
- **Error Proxying** - Calculator validation errors passed through
- **Unified Endpoint** - Single `/calculate-price` endpoint
- **File Analysis** - Automatic parameter extraction from STP/STL files

**Key Integration Points**:
```python
# Calculator service proxy
async def call_calculator_service(
    endpoint: str,
    data: dict,
    timeout: int = 30
) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALCULATOR_SERVICE_URL}{endpoint}",
            json=data,
            timeout=timeout
        )
        return response.json()
```

### Bitrix24 CRM Integration

**Integration Features**:
- **Asynchronous Sync** - Queue-based synchronization
- **Retry Logic** - Automatic retry with exponential backoff
- **Webhook Support** - Receive Bitrix events
- **Invoice Management** - Download and store invoices

**Sync Queue Model**:
```python
class BitrixSyncQueue(Base):
    __tablename__ = "bitrix_sync_queue"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String)  # deal/contact/lead
    entity_id = Column(Integer)
    bitrix_id = Column(String, nullable=True)
    status = Column(String)  # pending/completed/failed
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
```

## 🔐 Authentication & Authorization

### JWT Implementation

**Token Structure**:
```python
{
    "sub": "username",
    "exp": 1234567890,
    "iat": 1234567890,
    "is_admin": false
}
```

**Authentication Flow**:
1. User submits credentials via `/login`
2. Backend validates credentials against database
3. JWT token generated with user claims
4. Token returned to client
5. Client includes token in `Authorization: Bearer <token>` header
6. Backend validates token on protected endpoints

### Authorization Levels

1. **Anonymous** - No authentication required
   - Price calculations
   - Demo file access
   - Public endpoints

2. **Authenticated User** - Valid JWT token required
   - File uploads
   - Order creation
   - Profile management
   - Own file access

3. **Admin User** - Admin flag in JWT token
   - All user operations
   - All file access
   - Bitrix sync management
   - System administration

### Security Features

- **Password Hashing** - bcrypt with salt
- **Token Expiration** - Configurable token lifetime
- **CORS Protection** - Configurable origin restrictions
- **Input Validation** - Pydantic schema validation
- **SQL Injection Prevention** - SQLAlchemy ORM protection

## 📁 File Processing Pipeline

### File Upload Flow

1. **Client Upload** - Base64 encoded file data
2. **Validation** - File type and size validation
3. **Storage** - File saved to `uploads/` directory
4. **Database Record** - Metadata stored in database
5. **Preview Generation** - Asynchronous preview creation
6. **Access Control** - Permissions set based on user

### Preview Generation

**Supported Formats**:
- **STL Files** - Direct processing with trimesh
- **STP/STEP Files** - CadQuery → STL → Trimesh pipeline

**Preview Pipeline**:
```python
async def generate_preview(self, model_path: Path, preview_path: Path) -> bool:
    if model_path.suffix.lower() in ['.stl']:
        return await self._generate_stl_preview(model_path, preview_path)
    elif model_path.suffix.lower() in ['.stp', '.step']:
        return await self._generate_with_step_reader(model_path, preview_path)
    return False
```

### File Access Control

- **Demo Files** - Accessible to all users (IDs 1-5)
- **User Files** - Accessible to owner and admins
- **Admin Files** - Accessible to admins only

## 🧪 Testing Strategy

### Test Organization

**Test Structure**:
```
tests/
├── test_api_comprehensive.py      # Full API test suite
├── test_auth_endpoints.py         # Authentication tests
├── test_calculations_endpoints.py # Calculator integration tests
├── test_files_endpoints.py        # File management tests
├── test_orders_endpoints.py       # Order management tests
├── test_bitrix_endpoints.py       # Bitrix integration tests
├── test_call_requests_endpoints.py # Call request tests
└── test_integration_comprehensive.py # End-to-end tests
```

### Test Categories

1. **Unit Tests** - Individual function testing
2. **Integration Tests** - Module interaction testing
3. **API Tests** - Endpoint testing with real HTTP requests
4. **End-to-End Tests** - Complete workflow testing

### Test Execution

**Comprehensive Testing**:
```bash
python scripts/run_all_tests.py
```

**Quick Testing**:
```bash
python scripts/quick_test.py
```

**Specific Module Testing**:
```bash
python scripts/run_all_tests.py --suite auth
```

### Test Data Management

- **Demo Files** - Pre-loaded test files (IDs 1-5)
- **Test Users** - Admin and regular user accounts
- **Mock Services** - Calculator service mocking for offline testing
- **Database Isolation** - Each test uses clean database state

## 🔄 Development Workflow

### Local Development Setup

1. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

2. **Database Initialization**:
   ```bash
   # Database will be created automatically on first run
   # Admin user seeded automatically
   ```

3. **Service Startup**:
   ```bash
   # Terminal 1: Backend
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2: Calculator Service
   cd stl
   uvicorn main:app --reload --host 0.0.0.0 --port 7000
   ```

### Code Organization

**File Naming Conventions**:
- `router.py` - FastAPI route definitions
- `service.py` - Business logic
- `repository.py` - Database operations
- `models.py` - SQLAlchemy models
- `schemas.py` - Pydantic schemas

**Import Organization**:
```python
# Standard library imports
import asyncio
from typing import Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from backend.core.dependencies import get_db
from backend.models import User
from backend.schemas import UserCreate, UserOut
```

### Error Handling

**Custom Exceptions**:
```python
class BaseAPIException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class NotFoundException(BaseAPIException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)
```

**Global Error Handlers**:
```python
@app.exception_handler(BaseAPIException)
async def base_api_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )
```

## 🚀 Deployment Architecture

### Docker Configuration

**Multi-Service Setup**:
- **Backend Service** - Port 8000
- **Calculator Service** - Port 7000
- **Caddy Reverse Proxy** - Port 80/443
- **Database** - SQLite file (PostgreSQL planned)

**Docker Compose**:
```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/shop.db
      - CALCULATOR_SERVICE_URL=http://calculator:7000
  
  calculator:
    build: ./stl
    ports:
      - "7000:7000"
  
  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./caddy_certs:/data/caddy_certs
```

### Production Considerations

**Performance**:
- **Connection Pooling** - Database connection management
- **Async Operations** - Non-blocking I/O throughout
- **File Caching** - Preview image caching
- **Request Timeouts** - Configurable timeout settings

**Security**:
- **HTTPS** - Caddy reverse proxy with SSL
- **Environment Variables** - Sensitive data in environment
- **Input Validation** - Pydantic schema validation
- **CORS Configuration** - Restrictive CORS settings

**Monitoring**:
- **Health Checks** - `/health` endpoint
- **Structured Logging** - JSON-formatted logs
- **Error Tracking** - Comprehensive error logging
- **Performance Metrics** - Request timing and statistics

## 🗄️ PostgreSQL Migration Plan

### Migration Strategy

**Phase 1: Preparation**
- Remove Alembic infrastructure (completed)
- Document current schema
- Plan PostgreSQL schema design

**Phase 2: Implementation**
- Set up PostgreSQL database
- Create new Alembic configuration
- Implement data migration scripts
- Update connection strings

**Phase 3: Testing**
- Comprehensive testing with PostgreSQL
- Performance benchmarking
- Data integrity verification

**Phase 4: Deployment**
- Production migration
- Rollback procedures
- Monitoring and optimization

### PostgreSQL Benefits

- **Concurrency** - Multiple simultaneous connections
- **Performance** - Advanced query optimization
- **Scalability** - Horizontal scaling support
- **Production Ready** - Enterprise-grade features
- **Backup/Recovery** - Point-in-time recovery

## 🛠️ Future Roadmap

### Short Term (v3.1)
- PostgreSQL migration
- Performance optimizations
- Enhanced error handling
- Additional test coverage

### Medium Term (v3.2)
- ML pricing integration
- Advanced file analysis
- Real-time notifications
- API rate limiting

### Long Term (v4.0)
- Microservices architecture
- Event-driven design
- Advanced analytics
- Multi-tenant support

## 📊 Performance Considerations

### Database Optimization
- **Indexing** - Proper index design for queries
- **Query Optimization** - Efficient SQL queries
- **Connection Pooling** - Reuse database connections
- **Caching** - Redis for frequently accessed data

### File Processing
- **Async Processing** - Non-blocking file operations
- **Background Tasks** - Preview generation in background
- **File Compression** - Optimize storage usage
- **CDN Integration** - Fast file delivery

### API Performance
- **Response Caching** - Cache frequent responses
- **Pagination** - Efficient large dataset handling
- **Request Batching** - Batch multiple operations
- **Compression** - Gzip response compression

---

This development guide provides the technical foundation for understanding and extending the Manufacturing Service Backend. For specific implementation details, refer to the source code and API documentation.
