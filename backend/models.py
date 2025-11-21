from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, JSON
from sqlalchemy import Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    # User type: individual or legal
    user_type = Column(String, default="individual")  # "individual" or "legal"
    # Bitrix integration: linked Contact ID
    bitrix_contact_id = Column(Integer, nullable=True)
    # Optional profile fields
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    city = Column(String, nullable=True)
    company = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    payment_card_number = Column(String, nullable=True)
    # Additional fields for legal entities
    building = Column(String, nullable=True)
    region = Column(String, nullable=True)
    street = Column(String, nullable=True)
    postal = Column(String, nullable=True)
    # Payment fields for legal entities
    payment_company_name = Column(String, nullable=True)
    payment_inn = Column(String, nullable=True)
    payment_kpp = Column(String, nullable=True)
    payment_bik = Column(String, nullable=True)
    payment_bank_name = Column(String, nullable=True)
    payment_account = Column(String, nullable=True)
    payment_cor_account = Column(String, nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    orders = relationship('Order', back_populates='user')
    files = relationship('FileStorage', back_populates='user')
    documents = relationship('DocumentStorage', back_populates='user')

# Removed ManufacturingService model - now using calculator services directly

class FileStorage(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_metadata = Column(String, nullable=True)  # JSON object with extracted metadata
    # Demo/sample flag for anonymous calculations
    is_demo = Column(Boolean, default=False)
    # Preview image fields
    preview_filename = Column(String, nullable=True)  # e.g., "uuid_preview.png"
    preview_path = Column(String, nullable=True)      # Full path to preview image
    preview_generated = Column(Boolean, default=False)  # Generation status
    preview_generation_error = Column(String, nullable=True)  # Error message if failed
    user = relationship('User', back_populates='files')
    orders = relationship('Order', back_populates='file')

class DocumentStorage(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    document_category = Column(String, nullable=True)  # e.g., "drawing", "specification", "manual"
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_metadata = Column(String, nullable=True)  # JSON object with extracted metadata
    user = relationship('User', back_populates='documents')

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    service_id = Column(String)  # Calculator service ID (e.g., "cnc_lathe", "cnc_milling")
    file_id = Column(Integer, ForeignKey('files.id'))
    quantity = Column(Integer, default=1)
    dimensions = Column(String, nullable=True)  # JSON: {"length": 100, "width": 50, "height": 25} - deprecated, use length/width/height
    # New normalized dimension fields for easier querying and calculations
    length = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    thickness = Column(Integer, nullable=True)
    dia = Column(Integer, nullable=True)
    n_dimensions = Column(Integer, default=1)  # Number of dimensions provided
    # Additional field for Composite Rig
    composite_rig = Column(String, nullable=True)
    material_id = Column(String, default="alum_D16")  # Material ID from calculator service
    material_form = Column(String, default="rod")      # Material form
    special_instructions = Column(Text)
    status = Column(String, default="pending")  # pending, processing, completed, cancelled
    # Calculation coefficients
    k_otk = Column(String, default="1")  # OTK (quality control) coefficient, default "1"
    k_cert = Column(JSON, default=["a", "f"])  # Certification types
    # New identifiers replacing k_* across API/DB
    tolerance_id = Column(String, default="1")
    finish_id = Column(String, default="1")
    cover_id = Column(JSON, default=["1"])
    # Results from external calculator (second backend)
    mat_volume = Column(Float, nullable=True)
    detail_price = Column(Float, nullable=True)
    detail_price_one = Column(Float, nullable=True)  # Price per item without scale discounts
    total_price = Column(Float, nullable=True)
    mat_weight = Column(Float, nullable=True)
    mat_price = Column(Float, nullable=True)
    work_price = Column(Float, nullable=True)
    k_quantity = Column(Float, nullable=True)
    detail_time = Column(Float, nullable=True)
    k_complexity = Column(Float, nullable=True)  # Complexity coefficient from calculator service
    total_time = Column(Float, nullable=True)
    k_p = Column(Float, nullable=True)
    manufacturing_cycle = Column(Float, nullable=True)  # Manufacturing cycle from calculator service
    suitable_machines = Column(Text, nullable=True)  # JSON array of suitable manufacturing machines
    total_price_breakdown = Column(Text, nullable=True)  # JSON array of suitable manufacturing machines
    # Calculation type information
    calculation_type = Column(String, nullable=True)  # "ml_based", "rule_based", or "unknown"
    ml_model = Column(String, nullable=True)  # ML model name if available
    ml_confidence = Column(Float, nullable=True)  # ML confidence score if available
    # Calculation performance tracking
    calculation_time = Column(Float, nullable=True)  # Calculator service call duration only
    total_calculation_time = Column(Float, nullable=True)  # Total backend processing time
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Bitrix integration: linked Deal ID
    bitrix_deal_id = Column(Integer, nullable=True)
    # Invoice fields
    invoice_url = Column(String, nullable=True)  # Bitrix download URL
    invoice_file_path = Column(String, nullable=True)  # Local copy path
    invoice_generated_at = Column(DateTime, nullable=True)  # When invoice was generated
    # Additional documents attached to the order (JSON array of document IDs)
    document_ids = Column(Text, nullable=True)  # JSON: [1, 2, 3] - list of document IDs
    user = relationship('User', back_populates='orders')
    # Removed service relationship - now using calculator service IDs directly
    file = relationship('FileStorage', back_populates='orders')

class CallRequest(Base):
    __tablename__ = 'call_requests'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Optional user ID
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    product = Column(String, nullable=False)
    time = Column(String, nullable=False)
    additional = Column(Text, nullable=True)
    agreement = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Bitrix integration fields
    bitrix_lead_id = Column(Integer, nullable=True)  # Bitrix lead ID if created
    bitrix_contact_id = Column(Integer, nullable=True)  # Bitrix contact ID if created
    bitrix_synced_at = Column(DateTime, nullable=True)  # When last synced to Bitrix
    status = Column(String, default="new")  # new, contacted, completed, cancelled


class BitrixSyncQueue(Base):
    """Queue for Bitrix synchronization operations"""
    __tablename__ = 'bitrix_sync_queue'
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # 'deal', 'contact', 'lead'
    entity_id = Column(Integer, nullable=False)  # order_id, user_id, or call_request_id
    operation = Column(String, nullable=False)  # 'create', 'update'
    payload = Column(JSON, nullable=False)  # Data to sync
    status = Column(String, default="pending")  # pending, processing, completed, failed
    attempts = Column(Integer, default=0)  # Retry counter
    last_attempt = Column(DateTime, nullable=True)  # Last attempt timestamp
    error_message = Column(Text, nullable=True)  # Last error message
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))