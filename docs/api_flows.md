# API Request/Response Flow Diagrams

This document illustrates the request/response flows for all major operations in the Manufacturing Service API.

## 1. Authentication Flow

### User Registration
```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth Router
    participant AS as Auth Service
    participant U as Users Service
    participant DB as Database
    
    C->>A: POST /register
    A->>AS: validate_registration_data()
    AS->>AS: hash_password()
    AS->>U: create_user()
    U->>DB: INSERT user
    DB-->>U: user_id
    U-->>AS: user_created
    AS-->>A: success_response
    A-->>C: 201 Created
```

### User Login
```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth Router
    participant AS as Auth Service
    participant DB as Database
    
    C->>A: POST /login
    A->>AS: authenticate_user()
    AS->>DB: SELECT user by username
    DB-->>AS: user_data
    AS->>AS: verify_password()
    AS->>AS: create_access_token()
    AS-->>A: token + user_info
    A-->>C: 200 OK + JWT token
```

## 2. File Upload Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant F as Files Router
    participant FS as Files Service
    participant DB as Database
    participant S as Storage
    
    C->>F: POST /files (base64 data)
    F->>FS: upload_file_from_base64()
    FS->>FS: validate_file_type()
    FS->>S: save_file_to_disk()
    S-->>FS: file_path
    FS->>DB: INSERT file_record
    DB-->>FS: file_id
    FS->>FS: generate_preview_async()
    FS-->>F: file_info
    F-->>C: 200 OK + file_id
```

## 3. Calculation Flow (ML-Based)

### With File ID (File-Based Calculation)
```mermaid
sequenceDiagram
    participant C as Client
    participant CALC as Calculations Router
    participant FS as Files Service
    participant CS as Calculations Service
    participant CALC_SVC as Calculator Service (port 7000)
    participant DB as Database
    
    C->>CALC: POST /calculate-price (file_id)
    CALC->>FS: get_file_by_id()
    FS->>DB: SELECT file_record
    DB-->>FS: file_data
    FS->>FS: get_file_data_as_base64()
    FS-->>CALC: base64_file_data
    CALC->>CS: call_calculator_service()
    CS->>CS: map_file_type(stl/stp)
    CS->>CALC_SVC: POST /calculate-price (file_data)
    CALC_SVC->>CALC_SVC: ML calculation
    CALC_SVC-->>CS: calculation_result
    CS->>CS: extract_data_from_response()
    CS-->>CALC: mapped_result
    CALC-->>C: 200 OK + prices
```

### With Dimensions Only
```mermaid
sequenceDiagram
    participant C as Client
    participant CALC as Calculations Router
    participant CS as Calculations Service
    participant CALC_SVC as Calculator Service (port 7000)
    
    C->>CALC: POST /calculate-price (dimensions)
    CALC->>CS: call_calculator_service()
    CS->>CS: build_dimensions_payload()
    CS->>CALC_SVC: POST /calculate-price (dimensions)
    CALC_SVC->>CALC_SVC: rule-based calculation
    CALC_SVC-->>CS: calculation_result
    CS->>CS: extract_data_from_response()
    CS-->>CALC: mapped_result
    CALC-->>C: 200 OK + prices
```

## 4. Order Creation Flow

### With File (File-Based Order)
```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orders Router
    participant OS as Orders Service
    participant FS as Files Service
    participant CS as Calculations Service
    participant CALC_SVC as Calculator Service
    participant BS as Bitrix Sync Service
    participant DB as Database
    
    C->>O: POST /orders (file_id)
    O->>OS: create_order_with_calculation()
    OS->>FS: get_file_by_id()
    FS->>DB: SELECT file_record
    DB-->>FS: file_data
    FS->>FS: get_file_data_as_base64()
    FS-->>OS: base64_file_data
    OS->>CS: call_calculator_service()
    CS->>CALC_SVC: POST /calculate-price
    CALC_SVC-->>CS: calculation_result
    CS-->>OS: mapped_result
    OS->>DB: INSERT order
    DB-->>OS: order_id
    OS->>BS: queue_deal_creation()
    BS-->>OS: queued
    OS-->>O: order_created
    O-->>C: 200 OK + order_info
```

### With Dimensions Only
```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orders Router
    participant OS as Orders Service
    participant CS as Calculations Service
    participant CALC_SVC as Calculator Service
    participant BS as Bitrix Sync Service
    participant DB as Database
    
    C->>O: POST /orders (dimensions)
    O->>OS: create_order_with_dimensions()
    OS->>CS: call_calculator_service()
    CS->>CALC_SVC: POST /calculate-price
    CALC_SVC-->>CS: calculation_result
    CS-->>OS: mapped_result
    OS->>DB: INSERT order
    DB-->>OS: order_id
    OS->>BS: queue_deal_creation()
    BS-->>OS: queued
    OS-->>O: order_created
    O-->>C: 200 OK + order_info
```

## 5. Order Management Flow

### Order Update
```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orders Router
    participant OS as Orders Service
    participant DB as Database
    
    C->>O: PUT /orders/{order_id}
    O->>OS: update_order()
    OS->>DB: SELECT order
    DB-->>OS: order_data
    OS->>DB: UPDATE order
    DB-->>OS: updated_order
    OS-->>O: order_updated
    O-->>C: 200 OK + updated_order
```

### Order Recalculation
```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orders Router
    participant OS as Orders Service
    participant CS as Calculations Service
    participant CALC_SVC as Calculator Service
    participant DB as Database
    
    C->>O: POST /orders/{order_id}/recalculate
    O->>OS: recalculate_order_price()
    OS->>DB: SELECT order + file
    DB-->>OS: order_data
    OS->>CS: call_calculator_service()
    CS->>CALC_SVC: POST /calculate-price
    CALC_SVC-->>CS: new_calculation
    CS-->>OS: updated_prices
    OS->>DB: UPDATE order prices
    DB-->>OS: updated_order
    OS-->>O: recalculation_complete
    O-->>C: 200 OK + new_prices
```

## 6. Bitrix Integration Flow

### Contact Synchronization
```mermaid
sequenceDiagram
    participant BS as Bitrix Sync Service
    participant BC as Bitrix Client
    participant BITRIX as Bitrix CRM API
    participant DB as Database
    
    BS->>BC: sync_contact()
    BC->>BITRIX: POST /crm.contact.add
    BITRIX-->>BC: contact_id
    BC->>DB: UPDATE user bitrix_contact_id
    DB-->>BC: updated
    BC-->>BS: sync_complete
```

### Deal Creation from Order
```mermaid
sequenceDiagram
    participant BS as Bitrix Sync Service
    participant BC as Bitrix Client
    participant BITRIX as Bitrix CRM API
    participant DB as Database
    
    BS->>BC: create_deal_from_order()
    BC->>DB: SELECT order + user + file
    DB-->>BC: order_data
    BC->>BC: build_deal_payload()
    BC->>BITRIX: POST /crm.deal.add
    BITRIX-->>BC: deal_id
    BC->>DB: UPDATE order bitrix_deal_id
    DB-->>BC: updated
    BC-->>BS: deal_created
```

### Webhook Handling
```mermaid
sequenceDiagram
    participant BITRIX as Bitrix CRM
    participant WH as Webhook Router
    participant BS as Bitrix Service
    participant DB as Database
    
    BITRIX->>WH: POST /bitrix/webhook
    WH->>BS: handle_webhook()
    BS->>BS: validate_webhook_signature()
    BS->>BS: process_webhook_event()
    BS->>DB: UPDATE related records
    DB-->>BS: updated
    BS-->>WH: webhook_processed
    WH-->>BITRIX: 200 OK
```

## 7. Document Management Flow

### Document Upload
```mermaid
sequenceDiagram
    participant C as Client
    participant D as Documents Router
    participant DS as Documents Service
    participant DB as Database
    participant S as Storage
    
    C->>D: POST /documents (base64)
    D->>DS: upload_document()
    DS->>DS: validate_document_type()
    DS->>S: save_document_to_disk()
    S-->>DS: document_path
    DS->>DB: INSERT document_record
    DB-->>DS: document_id
    DS-->>D: document_info
    D-->>C: 200 OK + document_id
```

### Document Attachment to Order
```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orders Router
    participant OS as Orders Service
    participant DS as Documents Service
    participant DB as Database
    
    C->>O: POST /orders (document_ids)
    O->>OS: create_order_with_calculation()
    OS->>DS: get_documents_by_ids()
    DS->>DB: SELECT documents
    DB-->>DS: document_data
    DS-->>OS: documents
    OS->>DB: INSERT order
    OS->>DB: LINK order_documents
    DB-->>OS: order_created
    OS-->>O: order_with_documents
    O-->>C: 200 OK + order_info
```

## Key External API Calls

### Calculator Service (localhost:7000)
- **Purpose:** ML-based manufacturing price calculations
- **Key Endpoint:** `POST /calculate-price`
- **Input:** File data (base64) or dimensions + material parameters
- **Output:** Detailed pricing with ML prediction hours and complexity metrics

### Bitrix CRM API
- **Purpose:** Customer and deal management
- **Key Endpoints:** 
  - `POST /crm.contact.add` - Create contacts
  - `POST /crm.deal.add` - Create deals
  - `GET /crm.deal.list` - List deals
- **Authentication:** API key-based
- **Rate Limiting:** Handled by Bitrix client

