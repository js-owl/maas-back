# File Structure Documentation

## Project Overview

**Manufacturing Service API v3.1.0** - A modular FastAPI application providing manufacturing calculation services with ML-based pricing, file management, order processing, and Bitrix CRM integration.

**Technology Stack:**
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** SQLite (development), PostgreSQL (production)
- **Authentication:** JWT tokens with bcrypt password hashing
- **External Services:** Calculator service (port 7000), Bitrix CRM API
- **File Processing:** Trimesh, ezdxf, Pillow for 3D model analysis and preview generation

## Root Level Files

### Configuration Files
- **`requirements.txt`** - Python dependencies with pinned versions
- **`docker-compose.yml`** - Multi-service Docker configuration (API + calculator service)
- **`Dockerfile`** - Container configuration for the API service
- **`Caddyfile`** - Reverse proxy configuration for HTTPS termination
- **`pip.conf`** - Python package index configuration

### Database & Migration
- **`migrate_db.py`** - Database migration and seeding script
- **`free_port.py`** - Utility to find available ports for services

### Documentation
- **`README.md`** - Project overview and setup instructions
- **`FEATURES.md`** - Feature list and capabilities
- **`DEVELOPMENT.md`** - Development setup and guidelines

## Backend Structure (Modular Architecture)

### Core Module (`backend/core/`)
**Purpose:** Shared infrastructure and cross-cutting concerns

- **`config.py`** - Application configuration, environment variables, API version
- **`middleware.py`** - HTTPS redirect middleware for production
- **`error_handlers.py`** - Global exception handlers for different error types
- **`exceptions.py`** - Custom exception classes (BaseAPIException, etc.)
- **`dependencies.py`** - FastAPI dependency injection (database session, auth)
- **`base_repository.py`** - Base repository class with common CRUD operations

### Database Layer
- **`database.py`** - Database connection, session management, admin user seeding
- **`models.py`** - SQLAlchemy ORM models (User, FileStorage, Order, Document, etc.)
- **`schemas.py`** - Pydantic models for request/response validation and serialization

### Authentication Module (`backend/auth/`)
**Purpose:** User authentication and authorization

- **`router.py`** - Authentication endpoints (login, logout, register)
- **`service.py`** - Authentication business logic (password hashing, token generation)
- **`dependencies.py`** - Auth dependency functions (get_current_user, get_current_admin_user)

### Users Module (`backend/users/`)
**Purpose:** User management and profile operations

- **`router.py`** - User endpoints (profile management, admin user operations)
- **`service.py`** - User business logic (CRUD operations, profile updates)
- **`repository.py`** - User data access layer

### Files Module (`backend/files/`)
**Purpose:** 3D model file management and processing

- **`router.py`** - File endpoints (upload, download, list, delete, preview regeneration)
- **`service.py`** - File processing logic (base64 conversion, preview generation)
- **`repository.py`** - File data access layer
- **`storage.py`** - File storage utilities and path management
- **`preview.py`** - 3D model preview generation using trimesh

### Documents Module (`backend/documents/`)
**Purpose:** Document management for orders

- **`router.py`** - Document endpoints (upload, list, delete)
- **`service.py`** - Document processing logic
- **`repository.py`** - Document data access layer
- **`storage.py`** - Document storage utilities

### Calculations Module (`backend/calculations/`)
**Purpose:** Manufacturing price calculations via external calculator service

- **`router.py`** - Calculation endpoints (calculate-price, services, materials, coefficients)
- **`service.py`** - Calculator service integration (HTTP calls to port 7000)
- **`proxy.py`** - Proxy functions for calculator service endpoints

### Orders Module (`backend/orders/`)
**Purpose:** Order management and processing

- **`router.py`** - Order endpoints (create, read, update, delete, recalculate)
- **`service.py`** - Order business logic (creation with calculation, Bitrix sync)
- **`repository.py`** - Order data access layer
- **`invoice_service.py`** - Invoice generation and management

### Bitrix Module (`backend/bitrix/`)
**Purpose:** Bitrix CRM integration and synchronization

- **`router.py`** - Bitrix endpoints (sync contact, sync deal, webhook status)
- **`service.py`** - Bitrix API integration logic
- **`sync_service.py`** - Asynchronous synchronization service
- **`webhook_router.py`** - Webhook handlers for Bitrix events
- **`client.py`** - Bitrix API client with rate limiting

### Call Requests Module (`backend/call_requests/`)
**Purpose:** Customer call request management

- **`router.py`** - Call request endpoints (create, list, admin operations)
- **`service.py`** - Call request business logic
- **`repository.py`** - Call request data access layer

### Utilities (`backend/utils/`)
**Purpose:** Shared utility functions

- **`helpers.py`** - General helper functions
- **`logging.py`** - Logging configuration and utilities

### Main Application
- **`main.py`** - FastAPI application setup, middleware configuration, router registration

## Calculator Service (`stl/`)
**Purpose:** External ML-based manufacturing calculation service

**Note:** This service has its own documentation. The backend makes API calls to this service running on port 7000.

- **`main.py`** - Calculator service application
- **`constants.py`** - Service constants and configuration
- **`examples/`** - API usage examples and test scripts

## Tests Structure (`tests/`)
**Purpose:** Comprehensive test suite

- **`conftest.py`** - Pytest configuration and fixtures
- **`pytest.ini`** - Pytest settings
- **`test_*.py`** - Individual test modules for each component
- **`run_all_tests.py`** - Test runner script
- **`QUICK_START.md`** - Testing quick start guide

## Scripts (`scripts/`)
**Purpose:** Development and maintenance utilities

- **`quick_test.py`** - Quick API testing script
- **`run_all_tests.py`** - Test execution script
- **`run_pytest_tests.py`** - Pytest runner
- **`README.md`** - Scripts documentation

## Data Storage (`data/`, `uploads/`)
- **`data/shop.db`** - SQLite database file
- **`uploads/3d_models/`** - Uploaded 3D model files
- **`uploads/documents/`** - Uploaded document files
- **`uploads/previews/`** - Generated 3D model preview images
- **`uploads/invoices/`** - Generated invoice files

## Key Architectural Patterns

### Layered Architecture
1. **Router Layer** - HTTP endpoint handlers, request validation
2. **Service Layer** - Business logic, external API calls
3. **Repository Layer** - Data access, database operations

### Data Flow Pattern
```
Client Request → Router → Service → Repository → Database
                     ↓
              External APIs (Calculator, Bitrix)
                     ↓
              Response ← Router ← Service ← Repository
```

### Key Dependencies
- **Router → Service** - All routers depend on their corresponding service modules
- **Service → Repository** - Services use repositories for data access
- **Service → External APIs** - Calculator service (port 7000), Bitrix API
- **Cross-module** - All modules depend on core utilities and models

