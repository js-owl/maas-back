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
    personal_phone_number = Column(String, nullable=True)
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
    location = Column(Text, nullable=True)
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

class InvoiceStorage(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False, index=True)
    bitrix_document_id = Column(Integer, nullable=True)  # Bitrix document generator document ID
    generated_at = Column(DateTime, nullable=True)  # When invoice was generated in Bitrix
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    order = relationship('Order', back_populates='invoices')

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    service_id = Column(String)  # Calculator service ID (e.g., "cnc_lathe", "cnc_milling")
    file_id = Column(Integer, ForeignKey('files.id'))
    kit_id = Column(Integer, ForeignKey("kits.kit_id"), nullable=True, index=True)
    order_name = Column(String, nullable=True)  # Order name
    order_code = Column(String, nullable=True)
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
    status = Column(String, default="NEW")  # Bitrix stage names: NEW, PREPARATION, PREPAYMENT_INVOICE, EXECUTING, FINAL_INVOICE, WON, LOSE, APOLOGY
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
    # Invoice fields (DEPRECATED: Use invoice_ids column instead, kept for backward compatibility)
    invoice_url = Column(String, nullable=True)  # Bitrix download URL (deprecated)
    invoice_file_path = Column(String, nullable=True)  # Local copy path (deprecated)
    invoice_generated_at = Column(DateTime, nullable=True)  # When invoice was generated (deprecated)
    # User-uploaded technical documents attached to the order (JSON array of document IDs)
    # These are technical documents like drawings, specifications, etc. that support the main 3D model
    document_ids = Column(Text, nullable=True)  # JSON: [1, 2, 3] - list of user-uploaded document IDs
    # Bitrix-generated invoices attached to the order (JSON array of invoice IDs)
    # Invoices are generated by Bitrix and can be multiple (manager may make changes during deal processing)
    invoice_ids = Column(Text, nullable=True)  # JSON: [26, 27, 28] - list of invoice IDs (from invoices table)
    location = Column(Text, nullable=True) # DEPRECATED
    user = relationship('User', back_populates='orders')
    # Removed service relationship - now using calculator service IDs directly
    file = relationship('FileStorage', back_populates='orders')
    invoices = relationship('InvoiceStorage', back_populates='order')
    kit = relationship("Kit", back_populates="orders")
    
    @property
    def compute_front_status(self):
        """Compute stage names for front (without id from Bitrix)"""
        if not self.front_status:
            try:
                self.front_status = self.status.split(":")[1]
            except:
                self.front_status = self.status
            return self


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


class Kit(Base):
    __tablename__ = "kits"

    kit_id = Column(Integer, primary_key=True, index=True)
    order_ids = Column(Text, nullable=False, default="[]")  # JSON: [1, 2, 3] - list of order IDs
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kit_name = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    kit_price = Column(Float, nullable=True, default=0.0)

    delivery_price = Column(Float, nullable=True, default=0.0) # placeholder

    status = Column(String, default="NEW")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    bitrix_deal_id = Column(Integer, nullable=True) # Placeholder
    location = Column(Text, nullable=True)

    user = relationship("User", backref="kits")
    orders = relationship("Order", back_populates="kit")


class MaasBitrixIdsMapping(Base):
    """Mapping table for MaaS and Bitrix entity IDs"""
    __tablename__ = 'maas_bitrix_ids_mapping'
    
    id = Column(Integer, primary_key=True, index=True)
    maas_id = Column(Integer, nullable=False, index=True)
    bitrix_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(32), nullable=False, index=True)  # 'deal', 'contact', 'category', 'userfield_enum', etc.
    buffer = Column(JSON, nullable=True)  # Flexible JSON storage for additional data
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# --- Bitrix24 constant-entity source-of-truth tables (no bitrix_id on tables; use maas_bitrix_ids_mapping) ---

class BitrixCategory(Base):
    """Local source of truth for Bitrix24 categories (sales funnels). Columns align with backend.bitrix24.dto.category."""
    __tablename__ = 'bitrix_category'
    id = Column(Integer, primary_key=True, index=True)
    entity_type_id = Column(Integer, nullable=False)  # entityTypeId
    name = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    is_default = Column(Integer, nullable=True)  # SQLite: 0/1
    origin_id = Column(String, nullable=True)
    originator_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BitrixStatus(Base):
    """Local source of truth for Bitrix24 statuses. Columns align with backend.bitrix24.dto.status."""
    __tablename__ = 'bitrix_status'
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String, nullable=True)   # ENTITY_ID
    status_id = Column(String, nullable=True)   # STATUS_ID
    name = Column(String, nullable=True)        # NAME
    category_id = Column(Integer, nullable=True)
    semantics = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    color = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)
    name_init = Column(String, nullable=True)
    system = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BitrixUserfield(Base):
    """Local source of truth for Bitrix24 userfields. Columns align with backend.bitrix24.dto.userfield. LIST stored in bitrix_userfield_enum."""
    __tablename__ = 'bitrix_userfield'
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String, nullable=True)   # ENTITY_ID
    field_name = Column(String, nullable=True) # FIELD_NAME
    user_type_id = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    multiple = Column(String, nullable=True)
    mandatory = Column(String, nullable=True)
    show_filter = Column(String, nullable=True)
    show_in_list = Column(String, nullable=True)
    edit_in_list = Column(String, nullable=True)
    is_searchable = Column(String, nullable=True)
    label = Column(String, nullable=True)
    edit_form_label = Column(String, nullable=True)
    list_column_label = Column(String, nullable=True)
    list_filter_label = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    help_message = Column(String, nullable=True)
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enumerations = relationship('BitrixUserfieldEnum', back_populates='userfield')


class BitrixUserfieldEnum(Base):
    """List items for list-type userfields. FK to bitrix_userfield. Bitrix ID stored in maas_bitrix_ids_mapping (entity_type=userfield_enum)."""
    __tablename__ = 'bitrix_userfield_enum'
    id = Column(Integer, primary_key=True, index=True)
    userfield_id = Column(Integer, ForeignKey('bitrix_userfield.id', ondelete='CASCADE'), nullable=False, index=True)
    sort = Column(Integer, nullable=True)
    value = Column(String, nullable=True)   # VALUE
    def_ = Column(String, nullable=True)    # DEF (Y/N)
    xml_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    userfield = relationship('BitrixUserfield', back_populates='enumerations')


class BitrixProductProperty(Base):
    """Local source of truth for Bitrix24 product properties. Columns align with backend.bitrix24.dto.product_property."""
    __tablename__ = 'bitrix_product_property'
    id = Column(Integer, primary_key=True, index=True)
    iblock_id = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    code = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    active = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    is_required = Column(String, nullable=True)
    multiple = Column(String, nullable=True)
    multiple_cnt = Column(Integer, nullable=True)
    with_description = Column(String, nullable=True)
    hint = Column(String, nullable=True)
    row_count = Column(Integer, nullable=True)
    col_count = Column(Integer, nullable=True)
    searchable = Column(String, nullable=True)
    filtrable = Column(String, nullable=True)
    default_value = Column(String, nullable=True)
    list_type = Column(String, nullable=True)
    link_iblock_id = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    user_type = Column(String, nullable=True)
    user_type_settings = Column(JSON, nullable=True)
    timestamp_x = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enums = relationship('BitrixProductPropertyEnum', back_populates='property')


class BitrixProductPropertyEnum(Base):
    """Local source of truth for Bitrix24 product property enum values. Columns align with backend.bitrix24.dto.product_property_enum."""
    __tablename__ = 'bitrix_product_property_enum'
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('bitrix_product_property.id', ondelete='CASCADE'), nullable=False, index=True)
    value = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    def_ = Column(String, nullable=True)  # def (Y/N)
    sort = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    property = relationship('BitrixProductProperty', back_populates='enums')
