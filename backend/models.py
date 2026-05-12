from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, JSON
from sqlalchemy import Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime (no tzinfo).

    PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns require naive datetimes.
    asyncpg raises DataError when timezone-aware datetimes are passed to such columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    bitrix_contact_id = Column(Integer, nullable=True)
    building = Column(String, nullable=True)
    city = Column(String, nullable=True)
    company = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    location = Column(Text, nullable=True)
    must_change_password = Column(Boolean, default=False)
    office = Column(String, nullable=True)
    payment_account = Column(String, nullable=True)
    payment_bank_name = Column(String, nullable=True)
    payment_bik = Column(String, nullable=True)
    payment_card_number = Column(String, nullable=True)
    payment_company_name = Column(String, nullable=True)
    payment_cor_account = Column(String, nullable=True)
    payment_inn = Column(String, nullable=True)
    payment_kpp = Column(String, nullable=True)
    personal_phone_number = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    postal = Column(String, nullable=True)
    region = Column(String, nullable=True)
    street = Column(String, nullable=True)
    status = Column(String, default="active")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_type = Column(String, default="individual") # "individual" or "legal"
    username = Column(String, unique=True, index=True)
    # --- relationships ---
    documents = relationship('DocumentStorage', back_populates='user')
    files = relationship('FileStorage', back_populates='user')
    orders = relationship('Order', back_populates='user')


class FileStorage(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    file_metadata = Column(String, nullable=True)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    filename = Column(String, unique=True, index=True)
    is_demo = Column(Boolean, default=False)
    original_filename = Column(String)
    preview_filename = Column(String, nullable=True)
    preview_generated = Column(Boolean, default=False)
    preview_generation_error = Column(String, nullable=True)
    preview_path = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=utcnow)
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    # --- relationships ---
    orders = relationship('Order', back_populates='file')
    user = relationship('User', back_populates='files')


class DocumentStorage(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    document_category = Column(String, nullable=True)
    file_metadata = Column(String, nullable=True)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    filename = Column(String, unique=True, index=True)
    original_filename = Column(String)
    uploaded_at = Column(DateTime, default=utcnow)
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    # --- relationships ---
    user = relationship('User', back_populates='documents')


class InvoiceStorage(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    bitrix_document_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    file_path = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    filename = Column(String, unique=True, index=True)
    generated_at = Column(DateTime, nullable=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False, index=True)
    original_filename = Column(String)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    # --- relationships ---
    order = relationship('Order', back_populates='invoices')


class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    calculation_time = Column(Float, nullable=True)
    calculation_type = Column(String, nullable=True)
    cover_id = Column(JSON, default=["1"])
    created_at = Column(DateTime, default=utcnow)
    detail_price = Column(Float, nullable=True)
    detail_price_one = Column(Float, nullable=True)
    detail_price_calculation = Column(Text, nullable=True) # JSON 
    detail_time = Column(Float, nullable=True)
    document_ids = Column(Text, nullable=True)
    file_id = Column(Integer, ForeignKey('files.id'))
    finish_id = Column(String, default="1")
    height = Column(Integer, nullable=True)
    invoice_generated_at = Column(DateTime, nullable=True)
    invoice_ids = Column(Text, nullable=True) # JSON: [26, 27, 28] — list of invoice IDs from invoices table
    k_cert = Column(JSON, default=["a", "f"])
    k_otk = Column(String, default="1.0")
    k_quantity = Column(Float, nullable=True)
    kit_id = Column(Integer, ForeignKey("kits.kit_id"), nullable=True, index=True)
    length = Column(Integer, nullable=True)
    location = Column(Text, nullable=True)
    manufacturing_cycle = Column(Float, nullable=True)
    mat_price = Column(Float, nullable=True)
    mat_volume = Column(Float, nullable=True)
    mat_weight = Column(Float, nullable=True)
    material_form = Column(String, nullable=True)
    material_id = Column(String, nullable=True)
    ml_model = Column(String, nullable=True) # TODO
    order_code = Column(String, nullable=True)
    order_name = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    service_id = Column(String)
    special_instructions = Column(Text) # TODO
    status = Column(String, default="NEW") # Bitrix stage names
    suitable_machines = Column(Text, nullable=True) # JSON: [] — list of suitable machines
    tolerance_id = Column(String, default="1")
    total_calculation_time = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    total_price_breakdown = Column(Text, nullable=True) # JSON 
    total_time = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    width = Column(Integer, nullable=True)
    work_price = Column(Float, nullable=True)
    # --- relationships ---
    file = relationship('FileStorage', back_populates='orders')
    invoices = relationship('InvoiceStorage', back_populates='order')
    kit = relationship("Kit", back_populates="orders")
    user = relationship('User', back_populates='orders')

    @property
    def compute_front_status(self):
        """Compute stage names for front (without id from Bitrix)"""
        if not self.front_status:
            try:
                self.front_status = self.status.split(":")[1]
            except Exception:
                self.front_status = self.status
            return self


class CallRequest(Base):
    __tablename__ = 'call_requests'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    additional = Column(Text, nullable=True)
    agreement = Column(Boolean, default=True)
    bitrix_contact_id = Column(Integer, nullable=True)
    bitrix_lead_id = Column(Integer, nullable=True)
    bitrix_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    product = Column(String, nullable=False)
    status = Column(String, default="new")
    time = Column(String, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)


class Kit(Base):
    __tablename__ = "kits"
    kit_id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    created_at = Column(DateTime, default=utcnow)
    delivery_price = Column(Float, nullable=True, default=0.0)
    kit_name = Column(String, nullable=True)
    kit_price = Column(Float, nullable=True, default=0.0)
    location = Column(Text, nullable=True)
    manufacturing_cycle = Column(Text, nullable=True) # TODO
    order_ids = Column(Text, nullable=False, default="[]") # JSON: [1, 2, 3] — list of order IDs
    quantity = Column(Integer, default=1)
    status = Column(String, default="NEW")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # --- relationships ---
    orders = relationship("Order", back_populates="kit")
    user = relationship("User", backref="kits")


class MaasBitrixIdsMapping(Base):
    """Mapping table for MaaS and Bitrix entity IDs"""
    __tablename__ = 'maas_bitrix_ids_mapping'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    bitrix_id = Column(Integer, nullable=False, index=True)
    # Flexible JSON storage for additional data
    buffer = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    # 'deal', 'contact', 'category', 'userfield_enum', etc.
    entity_type = Column(String(32), nullable=False, index=True)
    maas_id = Column(Integer, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# --- Bitrix24 constant-entity source-of-truth tables ---
# (no bitrix_id on these tables; use maas_bitrix_ids_mapping)

class BitrixCategory(Base):
    """Local source of truth for Bitrix24 categories (sales funnels)."""
    __tablename__ = 'bitrix_category'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    created_at = Column(DateTime, default=utcnow)
    entity_type_id = Column(Integer, nullable=False)
    is_default = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    origin_id = Column(String, nullable=True)
    originator_id = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class BitrixStatus(Base):
    """Local source of truth for Bitrix24 statuses."""
    __tablename__ = 'bitrix_status'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    category_id = Column(Integer, nullable=True)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    entity_id = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)
    name = Column(String, nullable=True)
    name_init = Column(String, nullable=True)
    semantics = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    status_id = Column(String, nullable=True)
    system = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class BitrixUserfield(Base):
    """Local source of truth for Bitrix24 userfields. LIST stored in bitrix_userfield_enum."""
    __tablename__ = 'bitrix_userfield'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    created_at = Column(DateTime, default=utcnow)
    edit_form_label = Column(String, nullable=True)
    edit_in_list = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    field_name = Column(String, nullable=True)
    help_message = Column(String, nullable=True)
    is_searchable = Column(String, nullable=True)
    label = Column(String, nullable=True)
    list_column_label = Column(String, nullable=True)
    list_filter_label = Column(String, nullable=True)
    mandatory = Column(String, nullable=True)
    multiple = Column(String, nullable=True)
    settings = Column(JSON, nullable=True)
    show_filter = Column(String, nullable=True)
    show_in_list = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_type_id = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    # --- relationships ---
    enumerations = relationship('BitrixUserfieldEnum', back_populates='userfield')


class BitrixUserfieldEnum(Base):
    """List items for list-type userfields. FK to bitrix_userfield."""
    __tablename__ = 'bitrix_userfield_enum'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    created_at = Column(DateTime, default=utcnow)
    def_ = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    userfield_id = Column(Integer, ForeignKey('bitrix_userfield.id', ondelete='CASCADE'), nullable=False, index=True)
    value = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    # --- relationships ---
    userfield = relationship('BitrixUserfield', back_populates='enumerations')


class BitrixProductProperty(Base):
    """Local source of truth for Bitrix24 product properties."""
    __tablename__ = 'bitrix_product_property'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    active = Column(String, nullable=True)
    code = Column(String, nullable=True)
    col_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    default_value = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    filtrable = Column(String, nullable=True)
    hint = Column(String, nullable=True)
    iblock_id = Column(Integer, nullable=True)
    is_required = Column(String, nullable=True)
    link_iblock_id = Column(Integer, nullable=True)
    list_type = Column(String, nullable=True)
    multiple = Column(String, nullable=True)
    multiple_cnt = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    row_count = Column(Integer, nullable=True)
    searchable = Column(String, nullable=True)
    sort = Column(Integer, nullable=True)
    timestamp_x = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user_type = Column(String, nullable=True)
    user_type_settings = Column(JSON, nullable=True)
    with_description = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    # --- relationships ---
    enums = relationship('BitrixProductPropertyEnum', back_populates='property')


class BitrixProductPropertyEnum(Base):
    """List items for list-type product properties."""
    __tablename__ = 'bitrix_product_property_enum'
    id = Column(Integer, primary_key=True, index=True)
    # --- columns (alphabetical) ---
    created_at = Column(DateTime, default=utcnow)
    def_ = Column(String, nullable=True)
    property_id = Column(Integer, ForeignKey('bitrix_product_property.id', ondelete='CASCADE'), nullable=False, index=True)
    sort = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    value = Column(String, nullable=True)
    xml_id = Column(String, nullable=True)
    # --- relationships ---
    property = relationship('BitrixProductProperty', back_populates='enums')
