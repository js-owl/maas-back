# Architecture Diagrams - Function Call Flows

This document shows the detailed function call flows for all API endpoints, illustrating the layered architecture and dependencies.

## Layered Architecture Overview

The API follows a three-layer architecture pattern:

```
┌─────────────────┐
│   Router Layer  │ ← HTTP endpoints, request validation, response formatting
├─────────────────┤
│  Service Layer  │ ← Business logic, external API calls, data processing
├─────────────────┤
│Repository Layer │ ← Database operations, data access
└─────────────────┘
```

**Key Dependencies:**
- Router → Service (business logic)
- Service → Repository (data access)
- Service → External APIs (calculator service, Bitrix)
- All layers → Core utilities (logging, config, models)

## 1. Authentication Endpoints

### POST /register
```mermaid
flowchart TD
    A["POST /register"] --> B["Auth Router: register()"]
    B --> C["Auth Service: validate_registration_data()"]
    C --> D["Auth Service: hash_password()"]
    D --> E["Users Service: create_user()"]
    E --> F["Users Repository: create_user()"]
    F --> G[("Database: INSERT user")]
    G --> H["Auth Service: create_access_token()"]
    H --> I["Return: 201 Created + token"]
```

### POST /login
```mermaid
flowchart TD
    A["POST /login"] --> B["Auth Router: login()"]
    B --> C["Auth Service: authenticate_user()"]
    C --> D["Users Repository: get_user_by_username()"]
    D --> E[("Database: SELECT user")]
    E --> F["Auth Service: verify_password()"]
    F --> G["Auth Service: create_access_token()"]
    G --> H["Return: 200 OK + JWT token"]
```

### POST /logout
```mermaid
flowchart TD
    A["POST /logout"] --> B["Auth Router: logout()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Auth Service: decode_access_token()"]
    D --> E["Return: 200 OK + logout message"]
```

## 2. User Endpoints

### GET /profile
```mermaid
flowchart TD
    A["GET /profile"] --> B["Users Router: get_profile()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Return: 200 OK + user profile"]
```

### PUT /profile
```mermaid
flowchart TD
    A["PUT /profile"] --> B["Users Router: update_profile()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Users Service: update_user()"]
    D --> E["Users Repository: update_user()"]
    E --> F[("Database: UPDATE user")]
    F --> G["Return: 200 OK + updated profile"]
```

### GET /users (Admin)
```mermaid
flowchart TD
    A["GET /users"] --> B["Users Router: get_users()"]
    B --> C["Auth Dependencies: get_current_admin_user()"]
    C --> D["Users Service: get_users()"]
    D --> E["Users Repository: get_all()"]
    E --> F[("Database: SELECT users")]
    F --> G["Return: 200 OK + users list"]
```

## 3. File Endpoints

### POST /files
```mermaid
flowchart TD
    A["POST /files"] --> B["Files Router: upload_file_json()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Files Service: upload_file_from_base64()"]
    D --> E["Files Service: validate_file_type()"]
    E --> F["Files Storage: save_file_to_disk()"]
    F --> G["Files Repository: create_file_record()"]
    G --> H[("Database: INSERT file")]
    H --> I["Files Service: generate_preview_async()"]
    I --> J["Return: 200 OK + file info"]
```

### GET /files
```mermaid
flowchart TD
    A["GET /files"] --> B["Files Router: list_files()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Files Service: get_files_by_user()"]
    D --> E["Files Repository: get_files_by_user()"]
    E --> F[("Database: SELECT files")]
    F --> G["Return: 200 OK + files list"]
```

### GET /files/{file_id}
```mermaid
flowchart TD
    A["GET /files/{file_id}"] --> B["Files Router: get_file()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Files Service: get_file_by_id()"]
    D --> E["Files Repository: get_file_by_id()"]
    E --> F[("Database: SELECT file")]
    F --> G["Return: 200 OK + file info"]
```

### GET /files/{file_id}/download
```mermaid
flowchart TD
    A["GET /files/{file_id}/download"] --> B["Files Router: download_file()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Files Service: get_file_download_path()"]
    D --> E["Files Storage: get_file_path()"]
    E --> F["Return: FileResponse with file content"]
```

## 4. Document Endpoints

### POST /documents
```mermaid
flowchart TD
    A["POST /documents"] --> B["Documents Router: upload_document()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Documents Service: upload_document()"]
    D --> E["Documents Storage: save_document_to_disk()"]
    E --> F["Documents Repository: create_document()"]
    F --> G[("Database: INSERT document")]
    G --> H["Return: 200 OK + document info"]
```

### GET /documents
```mermaid
flowchart TD
    A["GET /documents"] --> B["Documents Router: list_documents()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Documents Service: get_documents_by_user()"]
    D --> E["Documents Repository: get_documents_by_user()"]
    E --> F[("Database: SELECT documents")]
    F --> G["Return: 200 OK + documents list"]
```

## 5. Calculation Endpoints

### POST /calculate-price (Main Endpoint)
```mermaid
flowchart TD
    A["POST /calculate-price"] --> B["Calculations Router: calculate_price()"]
    B --> C["Auth Dependencies: get_current_user() - optional"]
    C --> D{"File ID provided?"}
    
    D -->|Yes| E["Files Service: get_file_by_id()"]
    E --> F["Files Service: get_file_data_as_base64()"]
    F --> G["Calculations Service: call_calculator_service()"]
    
    D -->|No| H["Calculations Service: call_calculator_service()"]
    
    G --> I["Calculator Service: POST /calculate-price"]
    H --> I
    I --> J["Calculator Service: ML/Rule-based calculation"]
    J --> K["Calculations Service: extract_data_from_response()"]
    K --> L["Calculations Router: map_response_fields()"]
    L --> M["Return: 200 OK + calculation result"]
```

### GET /services
```mermaid
flowchart TD
    A["GET /services"] --> B["Calculations Router: list_services()"]
    B --> C["Calculations Proxy: get_services()"]
    C --> D["Calculator Service: GET /services"]
    D --> E["Return: 200 OK + services list"]
```

### GET /materials
```mermaid
flowchart TD
    A["GET /materials"] --> B["Calculations Router: get_calculator_materials()"]
    B --> C["Calculations Proxy: get_materials()"]
    C --> D["Calculator Service: GET /materials"]
    D --> E["Return: 200 OK + materials list"]
```

## 6. Order Endpoints

### POST /orders
```mermaid
flowchart TD
    A["POST /orders"] --> B["Orders Router: create_order()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D{"File ID provided?"}
    
    D -->|Yes| E["Orders Service: create_order_with_calculation()"]
    E --> F["Files Service: get_file_by_id()"]
    F --> G["Files Service: get_file_data_as_base64()"]
    G --> H["Calculations Service: call_calculator_service()"]
    
    D -->|No| I["Orders Service: create_order_with_dimensions()"]
    I --> J["Calculations Service: call_calculator_service()"]
    
    H --> K["Calculator Service: POST /calculate-price"]
    J --> K
    K --> L["Orders Repository: create_order()"]
    L --> M[("Database: INSERT order")]
    M --> N["Bitrix Sync Service: queue_deal_creation()"]
    N --> O["Return: 200 OK + order info"]
```

### GET /orders
```mermaid
flowchart TD
    A["GET /orders"] --> B["Orders Router: list_orders()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Orders Service: get_orders_by_user()"]
    D --> E["Orders Repository: get_orders_by_user()"]
    E --> F[("Database: SELECT orders")]
    F --> G["Return: 200 OK + orders list"]
```

### PUT /orders/{order_id}
```mermaid
flowchart TD
    A["PUT /orders/{order_id}"] --> B["Orders Router: update_order()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Orders Service: update_order()"]
    D --> E["Orders Repository: update_order()"]
    E --> F[("Database: UPDATE order")]
    F --> G["Return: 200 OK + updated order"]
```

### POST /orders/{order_id}/recalculate
```mermaid
flowchart TD
    A["POST /orders/{order_id}/recalculate"] --> B["Orders Router: recalculate_order()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Orders Service: recalculate_order_price()"]
    D --> E["Orders Repository: get_order_by_id()"]
    E --> F[("Database: SELECT order")]
    F --> G["Calculations Service: call_calculator_service()"]
    G --> H["Calculator Service: POST /calculate-price"]
    H --> I["Orders Repository: update_order_calc_fields()"]
    I --> J[("Database: UPDATE order prices")]
    J --> K["Return: 200 OK + new prices"]
```

## 7. Bitrix Endpoints

### POST /bitrix/sync-contact
```mermaid
flowchart TD
    A["POST /bitrix/sync-contact"] --> B["Bitrix Router: sync_contact()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Bitrix Service: sync_contact()"]
    D --> E["Bitrix Client: sync_contact()"]
    E --> F["Bitrix API: POST /crm.contact.add"]
    F --> G["Users Repository: update_user()"]
    G --> H[("Database: UPDATE user bitrix_contact_id")]
    H --> I["Return: 200 OK + sync status"]
```

### POST /bitrix/sync-deal
```mermaid
flowchart TD
    A["POST /bitrix/sync-deal"] --> B["Bitrix Router: sync_deal()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Bitrix Service: create_deal_from_order()"]
    D --> E["Orders Repository: get_order_by_id()"]
    E --> F[("Database: SELECT order")]
    F --> G["Bitrix Client: create_deal_from_order()"]
    G --> H["Bitrix API: POST /crm.deal.add"]
    H --> I["Orders Repository: update_order()"]
    I --> J[("Database: UPDATE order bitrix_deal_id")]
    J --> K["Return: 200 OK + deal info"]
```

### POST /bitrix/webhook
```mermaid
flowchart TD
    A["POST /bitrix/webhook"] --> B["Bitrix Webhook Router: handle_webhook()"]
    B --> C["Bitrix Service: handle_webhook()"]
    C --> D["Bitrix Service: validate_webhook_signature()"]
    D --> E["Bitrix Service: process_webhook_event()"]
    E --> F[("Database: UPDATE related records")]
    F --> G["Return: 200 OK"]
```

## 8. Call Request Endpoints

### POST /call-requests
```mermaid
flowchart TD
    A["POST /call-requests"] --> B["Call Requests Router: create_call_request()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Call Requests Service: create_call_request()"]
    D --> E["Call Requests Repository: create_call_request()"]
    E --> F[("Database: INSERT call_request")]
    F --> G["Return: 200 OK + call request info"]
```

### GET /call-requests
```mermaid
flowchart TD
    A["GET /call-requests"] --> B["Call Requests Router: list_call_requests()"]
    B --> C["Auth Dependencies: get_current_user()"]
    C --> D["Call Requests Service: get_call_requests_by_user()"]
    D --> E["Call Requests Repository: get_call_requests_by_user()"]
    E --> F[("Database: SELECT call_requests")]
    F --> G["Return: 200 OK + call requests list"]
```

## Key External API Integration Points

### Calculator Service Integration
- **Service:** `backend/calculations/service.py`
- **Key Function:** `call_calculator_service()`
- **External Endpoint:** `http://localhost:7000/calculate-price`
- **Purpose:** ML-based manufacturing price calculations
- **File Type Mapping:** STL → "stl", STP → "stp" (fixed in recent updates)

### Bitrix CRM Integration
- **Service:** `backend/bitrix/service.py`
- **Client:** `backend/bitrix/client.py`
- **Sync Service:** `backend/bitrix/sync_service.py`
- **External API:** Bitrix CRM REST API
- **Purpose:** Customer and deal synchronization

## Error Handling Flow

```mermaid
flowchart TD
    A["API Request"] --> B["Router Layer"]
    B --> C["Service Layer"]
    C --> D["Repository Layer"]
    D --> E[("Database")]
    
    B --> F["Validation Error"]
    C --> G["Business Logic Error"]
    D --> H["Database Error"]
    E --> I["SQL Error"]
    
    F --> J["HTTP 422 Unprocessable Entity"]
    G --> K["HTTP 400 Bad Request"]
    H --> L["HTTP 500 Internal Server Error"]
    I --> M["HTTP 500 Internal Server Error"]
    
    J --> N["Error Response to Client"]
    K --> N
    L --> N
    M --> N
```

## Authentication Flow in All Endpoints

```mermaid
flowchart TD
    A["API Request"] --> B["Router Endpoint"]
    B --> C["Auth Dependency: get_current_user()"]
    C --> D["Auth Service: decode_access_token()"]
    D --> E{"Token Valid?"}
    E -->|Yes| F["Extract User Info"]
    E -->|No| G["HTTP 401 Unauthorized"]
    F --> H["Continue to Business Logic"]
    G --> I["Return Error Response"]
    H --> J["Process Request"]
```

This architecture ensures clean separation of concerns, maintainable code, and robust error handling throughout the application.
