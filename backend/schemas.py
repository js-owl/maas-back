from pydantic import BaseModel, validator, field_validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str
    user_type: str  # "individual" or "legal" - required field
    email: Optional[str] = None
    full_name: Optional[str] = None
    city: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    payment_card_number: Optional[str] = None
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v not in ['individual', 'legal']:
            raise ValueError('user_type must be either "individual" or "legal"')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('username cannot be empty')
        if len(v) < 3:
            raise ValueError('username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('username must be no more than 50 characters long')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('password cannot be empty')
        if len(v) < 6:
            raise ValueError('password must be at least 6 characters long')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            if v.strip() == "":
                # Reject empty strings
                raise ValueError('email cannot be empty')
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('email must be a valid email address')
            # Additional check for double dots
            if '..' in v.strip():
                raise ValueError('email cannot contain consecutive dots')
            return v.strip()
        return None

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    user_type: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    city: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    payment_card_number: Optional[str] = None
    # Additional fields for legal entities
    building: Optional[str] = None
    region: Optional[str] = None
    street: Optional[str] = None
    postal: Optional[str] = None
    # Payment fields for legal entities
    payment_company_name: Optional[str] = None
    payment_inn: Optional[str] = None
    payment_kpp: Optional[str] = None
    payment_bik: Optional[str] = None
    payment_bank_name: Optional[str] = None
    payment_account: Optional[str] = None
    payment_cor_account: Optional[str] = None
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v is not None and v not in ['individual', 'legal']:
            raise ValueError('user_type must be either "individual" or "legal"')
        return v
    
    @validator('payment_inn')
    def validate_payment_inn(cls, v, values):
        user_type = values.get('user_type')
        if user_type == 'legal' and v is not None and len(v) < 10:
            raise ValueError('payment_inn must be at least 10 characters for legal entities')
        return v
    
    @validator('payment_kpp')
    def validate_payment_kpp(cls, v, values):
        user_type = values.get('user_type')
        if user_type == 'legal' and v is not None and len(v) < 9:
            raise ValueError('payment_kpp must be at least 9 characters for legal entities')
        return v
    
    @validator('payment_bik')
    def validate_payment_bik(cls, v, values):
        user_type = values.get('user_type')
        if user_type == 'legal' and v is not None and len(v) < 9:
            raise ValueError('payment_bik must be at least 9 characters for legal entities')
        return v

class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    must_change_password: bool
    user_type: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    city: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    payment_card_number: Optional[str] = None
    # Additional fields for legal entities
    building: Optional[str] = None
    region: Optional[str] = None
    street: Optional[str] = None
    postal: Optional[str] = None
    # Payment fields for legal entities
    payment_company_name: Optional[str] = None
    payment_inn: Optional[str] = None
    payment_kpp: Optional[str] = None
    payment_bik: Optional[str] = None
    payment_bank_name: Optional[str] = None
    payment_account: Optional[str] = None
    payment_cor_account: Optional[str] = None
    # Bitrix integration
    bitrix_contact_id: Optional[int] = None
    # Timestamps
    created_at: datetime
    
    class Config:
        from_attributes = True

# Removed manufacturing service schemas - now using calculator services directly
    
    class Config:
        from_attributes = True

# File Storage schemas
class FileStorageOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    uploaded_by: int
    uploaded_at: datetime
    file_metadata: Optional[str] = None
    is_demo: Optional[bool] = None
    # Preview image fields
    preview_filename: Optional[str] = None
    preview_path: Optional[str] = None
    preview_generated: Optional[bool] = None
    preview_generation_error: Optional[str] = None
    
    class Config:
        from_attributes = True

# Document Storage schemas
class DocumentStorageOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    document_category: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime
    file_metadata: Optional[str] = None
    
    class Config:
        from_attributes = True

class InvoiceOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_type: str
    order_id: int
    bitrix_document_id: Optional[int] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUpload(BaseModel):
    document_category: Optional[str] = None  # e.g., "drawing", "specification", "manual"

class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    document_category: Optional[str] = None

# Order schemas
class OrderCreate(BaseModel):
    service_id: str  # Calculator service ID (e.g., "cnc_lathe", "cnc_milling")
    order_name: Optional[str] = None  # Order name
    quantity: int = 1
    # Accept either JSON string or separate fields
    #dimensions: Optional[str] = None  # COMMENTED OUT: dimensions field no longer needed when length/width/height provided
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thickness: Optional[int] = None
    dia: Optional[int] = None
    n_dimensions: int = 1  # Number of dimensions provided
    composite_rig: Optional[str] = None
    material_id: str = "alum_D16"  # Material ID from calculator service (e.g., "alum_D16", "steel_304")
    material_form: str = "rod"      # Material form (e.g., "rod", "plate", "sheet", "bar")
    special_instructions: Optional[str] = None
    k_otk: str = "1"  # OTK (quality control) coefficient, default "1"
    k_cert: List[str] = ["a", "f"]  # Certification types
    tolerance_id: str = "1"
    finish_id: str = "1"
    cover_id: List[str] = ["1"]
    location: Optional[str] = None
    
    @validator('cover_id', pre=True)
    def parse_cover_id(cls, v):
        if v is None:
            return ["1"]
        if isinstance(v, str):
            try:
                # Try to parse as JSON array
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single string
                return [str(v)]
        elif isinstance(v, list):
            return [str(item) for item in v]
        else:
            return ["1"]
    # Additional documents attached to the order
    document_ids: Optional[List[int]] = None  # List of document IDs to attach to the order

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        return v

    #@validator('dimensions')  # COMMENTED OUT: dimensions field no longer needed
    #def validate_dimensions_json(cls, v):
    #    if v is None:
    #        return v
    #    try:
    #        dims = json.loads(v)
    #        required_keys = ['length', 'width', 'height']
    #        if not all(key in dims for key in required_keys):
    #            raise ValueError('Dimensions must include length, width, and height')
    #        return v
    #    except json.JSONDecodeError:
    #        raise ValueError('Dimensions must be valid JSON string')

    @validator('height')
    def validate_dimensions_numbers(cls, v, values):
        # COMMENTED OUT: dimensions logic no longer needed
        # Run only after width and length potentially set; check trio provided or dimensions provided
        length = values.get('length')
        width = values.get('width')
        #dims_json = values.get('dimensions')  # COMMENTED OUT: dimensions field no longer needed
        #if dims_json is None and (length is None or width is None or v is None):
        #    # Allow validation at runtime in route; keep schema flexible for backward compat
        #    return v
        # If provided, ensure positive integers
        if v is not None and v <= 0:
            raise ValueError('height must be positive')
        if length is not None and length <= 0:
            raise ValueError('length must be positive')
        if width is not None and width <= 0:
            raise ValueError('width must be positive')
        return v

class OrderUpdate(BaseModel):
    service_id: Optional[str] = None  # Calculator service ID
    order_name: Optional[str] = None  # Order name
    quantity: Optional[int] = None
    status: Optional[str] = None
    special_instructions: Optional[str] = None
    material_id: Optional[str] = None  # Material ID from calculator service
    material_form: Optional[str] = None  # Material form
    composite_rig: Optional[str] = None
    file_id: Optional[int] = None
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    n_dimensions: Optional[int] = None  # Number of dimensions provided
    k_otk: Optional[str] = None  # OTK (quality control) coefficient
    tolerance_id: Optional[str] = None
    finish_id: Optional[str] = None
    cover_id: Optional[Any] = None  # Accept any type, will be validated and converted to List[str]
    # Additional documents attached to the order
    document_ids: Optional[List[int]] = None  # List of document IDs to attach to the order
    location: Optional[str] = None

    @field_validator('cover_id', mode='before')
    @classmethod
    def parse_cover_id(cls, v):
        """Parse cover_id from string/list to list for backward compatibility"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                # Try to parse as JSON array
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single string
                return [str(v)]
        elif isinstance(v, list):
            return [str(item) for item in v]
        else:
            # For any other type, try to convert to list
            return [str(v)]
    
    @field_validator('cover_id', mode='after')
    @classmethod
    def validate_cover_id_list(cls, v):
        """Ensure cover_id is always a List[str]"""
        if v is None:
            return None
        if not isinstance(v, list):
            return [str(v)]
        return [str(item) for item in v]

    @validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v < 1:
            raise ValueError('Quantity must be at least 1')
        return v

    @validator('status')
    def validate_status(cls, v):
        # Bitrix stage names (without C1: prefix)
        valid_statuses = ['NEW', 'PREPARATION', 'PREPAYMENT_INVOICE', 'EXECUTING', 'FINAL_INVOICE', 'WON', 'LOSE', 'APOLOGY']
        if v is not None and v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('height')
    def validate_dimensions_numbers(cls, v, values):
        # Run only after width and length potentially set
        length = values.get('length')
        width = values.get('width')
        # If provided, ensure positive integers
        if v is not None and v <= 0:
            raise ValueError('height must be positive')
        if length is not None and length <= 0:
            raise ValueError('length must be positive')
        if width is not None and width <= 0:
            raise ValueError('width must be positive')
        return v

class OrderOut(BaseModel):
    order_id: int
    user_id: int
    service_id: str  # Calculator service ID
    file_id: Optional[int] = None  # File ID may be None if file was deleted
    order_name: Optional[str] = None  # Order name
    quantity: int
    #dimensions: str  # COMMENTED OUT: dimensions field no longer needed when length/width/height provided
    length: Optional[int]
    width: Optional[int]
    height: Optional[int]
    n_dimensions: int  # Number of dimensions provided
    composite_rig: Optional[str]
    material_id: Optional[str]  # Material ID from calculator service
    material_form: Optional[str]  # Material form
    special_instructions: Optional[str]
    total_price_breakdown: Optional[Dict[str, Any]]
    status: str
    # Calculation coefficients
    k_otk: str = "1"  # OTK (quality control) coefficient, default "1"
    tolerance_id: str = "1"
    finish_id: str = "1"
    cover_id: List[str] = ["1"]
    
    @validator('cover_id', pre=True)
    def parse_cover_id(cls, v):
        if v is None:
            return ["1"]
        if isinstance(v, str):
            try:
                # Try to parse as JSON array
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single string
                return [str(v)]
        elif isinstance(v, list):
            return [str(item) for item in v]
        else:
            return ["1"]
    # persisted calc fields (optional)
    mat_volume: Optional[float] = None
    detail_price: Optional[float] = None
    detail_price_one: Optional[float] = None  # Price per item without scale discounts
    total_price: Optional[float] = None
    mat_weight: Optional[float] = None
    mat_price: Optional[float] = None
    work_price: Optional[float] = None
    k_quantity: Optional[float] = None
    k_complexity: Optional[float] = None  # Complexity coefficient from calculator service
    #k_p: Optional[float] = None  # COMMENTED OUT: k_p field no longer needed
    total_time: Optional[float] = None
    manufacturing_cycle: Optional[float] = None  # Manufacturing cycle from calculator service
    suitable_machines: Optional[List[str]] = None  # Suitable manufacturing machines
    location: Optional[str] = None
    # Calculation type information
    calculation_type: Optional[str] = None  # "ml_based", "rule_based", or "unknown"
    ml_model: Optional[str] = None  # ML model name if available
    ml_confidence: Optional[float] = None  # ML confidence score if available
    # Calculation performance tracking
    calculation_time: Optional[float] = None  # Calculator service call duration only
    total_calculation_time: Optional[float] = None  # Total backend processing time
    created_at: datetime
    updated_at: datetime
    # User-uploaded technical documents attached to the order
    document_ids: Optional[List[int]] = None  # List of user-uploaded document IDs
    # Bitrix-generated invoices attached to the order
    invoice_ids: Optional[List[int]] = None  # List of invoice document IDs
    # Removed service relationship - now using calculator service IDs directly
    message: Optional[str] = None
    
    @validator('document_ids', pre=True)
    def parse_document_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('invoice_ids', pre=True)
    def parse_invoice_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('suitable_machines', pre=True)
    def parse_suitable_machines(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('total_price_breakdown', pre=True)
    def parse_total_price_breakdown(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                parsed = json.loads(v)
                # Ensure it's a dictionary, not a list or other type
                if isinstance(parsed, dict):
                    return parsed
                else:
                    # If it's not a dict, return None or wrap it
                    return None
            except (json.JSONDecodeError, ValueError, TypeError):
                return None
        # If it's already a dict, return as-is
        if isinstance(v, dict):
            return v
        return None
    
    class Config:
        from_attributes = True

class OrderOutSimple(BaseModel):
    order_id: int
    user_id: int
    service_id: str  # Calculator service ID
    file_id: Optional[int] = None  # File ID may be None if file was deleted
    order_name: Optional[str] = None  # Order name
    quantity: int
    #dimensions: str  # COMMENTED OUT: dimensions field no longer needed when length/width/height provided
    length: Optional[int]
    width: Optional[int]
    height: Optional[int]
    n_dimensions: int  # Number of dimensions provided
    composite_rig: Optional[str]
    material_id: Optional[str]  # Material ID from calculator service
    material_form: Optional[str]  # Material form
    special_instructions: Optional[str]
    status: str
    # Calculation coefficients
    k_otk: str = "1"  # OTK (quality control) coefficient, default "1"
    tolerance_id: str = "1"
    finish_id: str = "1"
    cover_id: List[str] = ["1"]
    
    @validator('cover_id', pre=True)
    def parse_cover_id(cls, v):
        if v is None:
            return ["1"]
        if isinstance(v, str):
            try:
                # Try to parse as JSON array
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single string
                return [str(v)]
        elif isinstance(v, list):
            return [str(item) for item in v]
        else:
            return ["1"]
    # persisted calc fields (optional)
    mat_volume: Optional[float] = None
    detail_price: Optional[float] = None
    detail_price_one: Optional[float] = None  # Price per item without scale discounts
    total_price: Optional[float] = None
    mat_weight: Optional[float] = None
    mat_price: Optional[float] = None
    work_price: Optional[float] = None
    k_quantity: Optional[float] = None
    k_complexity: Optional[float] = None  # Complexity coefficient from calculator service
    #k_p: Optional[float] = None  # COMMENTED OUT: k_p field no longer needed
    total_time: Optional[float] = None
    manufacturing_cycle: Optional[float] = None  # Manufacturing cycle from calculator service
    suitable_machines: Optional[List[str]] = None  # Suitable manufacturing machines
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # User-uploaded technical documents attached to the order
    document_ids: Optional[List[int]] = None  # List of user-uploaded document IDs
    # Bitrix-generated invoices attached to the order
    invoice_ids: Optional[List[int]] = None  # List of invoice document IDs
    message: Optional[str] = None
    
    @validator('document_ids', pre=True)
    def parse_document_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('invoice_ids', pre=True)
    def parse_invoice_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('suitable_machines', pre=True)
    def parse_suitable_machines(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    class Config:
        from_attributes = True

        

class OrderWithDetails(BaseModel):
    id: int
    user_id: int
    service_id: str  # Calculator service ID
    file_id: int
    order_name: Optional[str] = None  # Order name
    quantity: int
    #dimensions: str  # COMMENTED OUT: dimensions field no longer needed when length/width/height provided
    length: Optional[int]
    width: Optional[int]
    height: Optional[int]
    n_dimensions: int  # Number of dimensions provided
    composite_rig: Optional[str]
    material_id: Optional[str]  # Material ID from calculator service
    material_form: Optional[str]  # Material form
    special_instructions: Optional[str]
    status: str
    # Calculation coefficients
    k_otk: str = "1"  # OTK (quality control) coefficient, default "1"
    tolerance_id: str = "1"
    finish_id: str = "1"
    cover_id: List[str] = ["1"]
    
    @validator('cover_id', pre=True)
    def parse_cover_id(cls, v):
        if v is None:
            return ["1"]
        if isinstance(v, str):
            try:
                # Try to parse as JSON array
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single string
                return [str(v)]
        elif isinstance(v, list):
            return [str(item) for item in v]
        else:
            return ["1"]
    # persisted calc fields (optional)
    mat_volume: Optional[float] = None
    detail_price: Optional[float] = None
    detail_price_one: Optional[float] = None  # Price per item without scale discounts
    total_price: Optional[float] = None
    mat_weight: Optional[float] = None
    mat_price: Optional[float] = None
    work_price: Optional[float] = None
    k_quantity: Optional[float] = None
    k_complexity: Optional[float] = None  # Complexity coefficient from calculator service
    #k_p: Optional[float] = None  # COMMENTED OUT: k_p field no longer needed
    total_time: Optional[float] = None
    manufacturing_cycle: Optional[float] = None  # Manufacturing cycle from calculator service
    suitable_machines: Optional[List[str]] = None  # Suitable manufacturing machines
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # User-uploaded technical documents attached to the order
    document_ids: Optional[List[int]] = None  # List of user-uploaded document IDs
    # Bitrix-generated invoices attached to the order
    invoice_ids: Optional[List[int]] = None  # List of invoice document IDs
    # Bitrix integration
    bitrix_deal_id: Optional[int] = None
    # Removed service relationship - now using calculator service IDs directly
    file: Optional[FileStorageOut] = None  # File may be None if deleted
    user: UserOut
    message: Optional[str] = None
    
    @validator('document_ids', pre=True)
    def parse_document_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    @validator('suitable_machines', pre=True)
    def parse_suitable_machines(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
    
    class Config:
        from_attributes = True


# Admin shape: same as OrderOut, but also includes user
class AdminOrderOut(OrderOut):
    user: UserOut



# Response schemas
class MessageResponse(BaseModel):
    message: str

class FileUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    message: str = "File uploaded successfully"

# List schemas
# Removed ManufacturingServicesList - now using calculator services directly

class OrdersList(BaseModel):
    orders: List[OrderOut]

class UsersList(BaseModel):
    users: List[UserOut] 

# Calculation result schema for order creation
class CalcOut(BaseModel):
    service_id: int
    quantity: int
    length: Optional[int]
    width: Optional[int]
    height: Optional[int]
    n_dimensions: int  # Number of dimensions provided
    k_otk: str = "1"  # OTK (quality control) coefficient, default "1"
    mat_volume: float
    detail_price: float
    mat_weight: float
    mat_price: float
    work_price: float
    k_quantity: float
    #k_p: float  # COMMENTED OUT: k_p field no longer needed
    total_time: float

# Order creation response schema
class OrderCreateResponse(BaseModel):
    order: OrderOutSimple
    calc: CalcOut

# Response with only order
class OrderOnlyResponse(BaseModel):
    order: OrderOutSimple

# External CRM order status update schema
class OrderStatusUpdate(BaseModel):
    status: str  # Just validate it's a string, no specific values restriction

# Call request schema
class CallRequestCreate(BaseModel):
    additional: Optional[str] = ""
    agreement: bool = True
    name: str
    phone: str
    product: str  # e.g., "machining", "printing", etc.
    time: str  # e.g., "14:00-15:00"

class CallRequestOut(BaseModel):
    id: int
    name: str
    phone: str
    product: str
    time: str
    additional: Optional[str] = None
    agreement: bool
    created_at: datetime
    updated_at: datetime
    bitrix_lead_id: Optional[int] = None
    bitrix_contact_id: Optional[int] = None
    status: str
    
    class Config:
        from_attributes = True

class CallRequestResponse(BaseModel):
    message: str
    call_request_id: int

# ============================================================================
# JSON Request Schemas (Form to JSON Conversion)
# ============================================================================

# Calculation request schema (replaces Form parameters)
# Note: Validation is minimal to allow calculator service to handle detailed validation
# Calculator accepts either file_data OR dimensions to trigger different algorithms
class CalculationRequest(BaseModel):
    service_id: str  # Only required field - must identify which calculator to use
    file_id: Optional[int] = None
    quantity: Optional[int] = None  # Made optional - calculator can handle missing
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thickness: Optional[int] = None
    dia: Optional[int] = None
    material_id: Optional[str] = None  # Made optional - calculator can handle missing
    material_form: Optional[str] = "rod"  # Make optional
    special_instructions: Optional[str] = None
    tolerance_id: Optional[str] = "1"  # Make optional
    finish_id: Optional[str] = "1"  # Make optional
    cover_id: Optional[List[str]] = None  # Make optional
    k_otk: Optional[str] = "1"  # Make optional
    k_cert: Optional[List[str]] = ["a", "f"]  # Make optional
    n_dimensions: Optional[int] = 1  # Make optional
    document_ids: Optional[List[int]] = None  # Document IDs for calculation context
    location: Optional[str] = None
    
    @validator('service_id')
    def validate_service_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('service_id cannot be empty')
        
        # Note: Service ID validation is handled by the calculator service
        # We only validate that it's not empty here
        return v.strip()
    
    # @validator('quantity')
    # def validate_quantity(cls, v):
    #     if v is None:
    #         raise ValueError('quantity is required')
    #     if not isinstance(v, int):
    #         raise ValueError('quantity must be an integer')
    #     if v <= 0:
    #         raise ValueError('quantity must be greater than 0')
    #     return v
    
    # @validator('material_id')
    # def validate_material_id(cls, v):
    #     if not v or len(v.strip()) == 0:
    #         raise ValueError('material_id cannot be empty')
    #     return v.strip()
    
    @validator('cover_id')
    def validate_cover_id(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError('cover_id must be a list or None')
        # Ensure all items in the list are strings
        for item in v:
            if not isinstance(item, str):
                raise ValueError('cover_id must contain only strings')
        return v

# File upload request schema (with base64 encoding)
class FileUploadRequest(BaseModel):
    file_name: str
    file_data: str  # base64 encoded
    file_type: str  # "stl", "stp", "step", etc.

# Document upload request schema (with base64 encoding)
class DocumentUploadRequest(BaseModel):
    document_name: str
    document_data: str  # base64 encoded
    document_category: Optional[str] = None

# Order creation request schema (replaces Form parameters)
# Calculator accepts either file_id OR dimensions to trigger different algorithms
class OrderCreateRequest(BaseModel):
    service_id: str
    # Optional human‑readable order name; router expects this field
    order_name: Optional[str] = None
    file_id: Optional[int] = None  # Made optional - can send dimensions instead
    quantity: int = 1
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thickness: Optional[int] = None
    dia: Optional[int] = None
    material_id: str = "alum_D16"
    material_form: str = "rod"
    special_instructions: Optional[str] = None
    tolerance_id: str = "1"  # Default value to match OrderCreate
    finish_id: str = "1"  # Default value to match OrderCreate
    cover_id: List[str] = ["1"]  # Default value to match OrderCreate
    k_otk: str = "1"  # Default value to match OrderCreate
    k_cert: List[str] = ["a", "f"]  # Default value to match OrderCreate
    n_dimensions: int = 1
    document_ids: Optional[List[int]] = []
    location: Optional[str] = None
    kit_id: Optional[int] = None


# Call Request schemas
class CallRequestStatusUpdate(BaseModel):
    status: str

class CallRequestBitrixUpdate(BaseModel):
    bitrix_lead_id: Optional[int] = None
    bitrix_contact_id: Optional[int] = None

# Standardized Response schemas
class SuccessResponse(BaseModel):
    """Standard success response format"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """Standard error response format"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    path: Optional[str] = None

class LoginResponse(BaseModel):
    """Login response format"""
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False

class LogoutResponse(BaseModel):
    """Logout response format"""
    message: str
    detail: str

class HealthResponse(BaseModel):
    """Health check response format"""
    status: str
    version: str
    timestamp: datetime
    services: Optional[Dict[str, str]] = None

# Create kit schemas
class KitCreate(BaseModel):
    kit_name: Optional[str] = None
    order_ids: List[int]
    user_id: int
    quantity: int = 1
    status: Optional[str] = "NEW"
    bitrix_deal_id: Optional[int] = None
    location: Optional[str] = None

    @validator("order_ids")
    def validate_order_ids(cls, v):
        if not v:
            raise ValueError("order_ids must be a non-empty list")
        return [int(x) for x in v]

    @validator("quantity")
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError("quantity must be >= 1")
        return v

class KitOut(BaseModel):
    kit_id: int
    order_ids: List[int]
    user_id: int
    kit_name: Optional[str] = None
    quantity: int
    kit_price: float | None = None
    total_kit_price: float | None = None

    delivery_price: float | None = None

    status: str
    created_at: datetime
    updated_at: datetime
    bitrix_deal_id: Optional[int] = None
    location: Optional[str] = None

    @validator("order_ids", pre=True)
    def parse_order_ids(cls, v):
        # Если прилетает TEXT из БД — это JSON-строка
        if v is None:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return v

    class Config:
        from_attributes = True


class KitUpdate(BaseModel):
    kit_name: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    bitrix_deal_id: Optional[int] = None
    location: Optional[str] = None
    order_ids: Optional[List[int]] = None
