# Manufacturing Service Backend v3.2.0

A comprehensive FastAPI backend for a manufacturing service platform that supports user management, 3D model file uploads, order processing with external calculator service integration, and Bitrix24 CRM integration.

## 🚀 Quick Start

### Docker Deployment (Recommended)

1. **Clone and start the services:**
   ```bash
   git clone <repository-url>
   cd maas-backend
   docker-compose up -d
   ```

2. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Calculator Service: http://localhost:7000/docs

### Local Development

1. **Setup environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

2. **Start the backend:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the calculator service:**
   ```bash
   cd stl
   uvicorn main:app --reload --host 0.0.0.0 --port 7000
   ```

## ✨ Features at a Glance

- **🔐 Authentication & Authorization** - JWT-based with admin roles
- **📁 File Management** - 3D model uploads (STL, STP/STEP) with automatic preview generation
- **💰 Price Calculations** - Integration with external calculator service for CNC, 3D printing, painting
- **📋 Order Management** - Complete order lifecycle with document attachments
- **🏢 CRM Integration** - Bitrix24 integration with automatic deal/contact creation
- **📞 Call Requests** - Lead management system
- **⏱️ Performance Tracking** - Comprehensive timing metrics for all calculations (v3.2.0)
- **🔧 Modular Architecture** - Clean, maintainable codebase with feature-based modules
- **📊 Comprehensive Testing** - Full test coverage for all endpoints
- **🐳 Docker Ready** - Production-ready containerization

## 🏗️ Architecture Overview

The backend follows a **modular architecture** with clear separation of concerns:

```
backend/
├── core/           # Shared configuration and dependencies
├── auth/           # Authentication and JWT management
├── users/          # User profile and management
├── files/          # 3D model file handling
├── documents/      # Document storage and management
├── calculations/   # Calculator service integration
├── orders/         # Order management and processing
├── bitrix/         # Bitrix24 CRM integration
├── call_requests/  # Call request management
└── utils/          # Utility functions and helpers
```

Each module follows the **Repository → Service → Router** pattern for clean, testable code.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/shop.db

# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Calculator Service
CALCULATOR_SERVICE_URL=http://localhost:7000

# Bitrix24 Integration (Optional)
BITRIX_ENABLED=false
BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.com/rest/1/your-webhook/
BITRIX_CLIENT_ID=your-client-id
BITRIX_CLIENT_SECRET=your-client-secret
```

### Calculator Service

The backend integrates with a separate calculator service running on port 7000. See the `stl/` directory for the calculator service implementation.

## 📖 API Usage Examples

### Authentication

**Default Credentials:**
- **Admin User**: `admin` / `admin123` (password already changed in development)
- **Test User**: `testuser` / `testpass123`

```bash
# Login as admin
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Login as test user
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer <token>" "http://localhost:8000/profile"
```

### File Upload

```bash
# Upload 3D model
curl -X POST "http://localhost:8000/files" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "model.stl",
    "file_data": "base64_encoded_content...",
    "file_type": "stl"
  }'
```

### Price Calculation

```bash
# Calculate price
curl -X POST "http://localhost:8000/calculate-price" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "material_id": "PA11",
    "material_form": "powder",
    "quantity": 1,
    "length": 100,
    "width": 100,
    "height": 10
  }'
```

### Order Creation

```bash
# Create order
curl -X POST "http://localhost:8000/orders" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "printing",
    "material_id": "PA11",
    "material_form": "powder",
    "quantity": 1,
    "file_id": 1,
    "cover_id": ["1"],
    "tolerance_id": "1",
    "finish_id": "1"
  }'
```

## 🧪 Testing

### Run All Tests

```bash
# Comprehensive test suite
python scripts/run_all_tests.py

# Quick functionality test
python scripts/quick_test.py

# Specific test suite
python scripts/run_all_tests.py --suite auth
```

### Test Coverage

- **Authentication & Users** - Login, registration, profile management
- **File Management** - Upload, download, preview generation
- **Calculations** - Price calculations with various parameters
- **Orders** - Order creation, management, document attachment
- **Bitrix Integration** - CRM synchronization (when enabled)
- **Call Requests** - Lead management system

## 🚀 Deployment

### Docker Production

```bash
# Build and start all services
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Production

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Set production environment variables
   - Configure database connection
   - Set up reverse proxy (Caddy/Nginx)

3. **Start services:**
   ```bash
   # Backend
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   
   # Calculator service
   uvicorn stl.main:app --host 0.0.0.0 --port 7000
   ```

## 📚 Documentation

- **[API Reference](docs/api_reference_v3.md)** - Complete API documentation
- **[Development Guide](DEVELOPMENT.md)** - Technical architecture and patterns
- **[Features Overview](FEATURES.md)** - Feature history and roadmap
- **[Migration Guide](docs/migration_guide_v2_to_v3.md)** - Frontend migration guide
- **[Authentication Guide](docs/authentication_and_permissions.md)** - Security documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the test cases for usage examples
- See [DEVELOPMENT.md](DEVELOPMENT.md) for technical details

---

**Version**: 3.0.0  
**Last Updated**: January 2025  
**Python**: 3.8+  
**FastAPI**: 0.100+