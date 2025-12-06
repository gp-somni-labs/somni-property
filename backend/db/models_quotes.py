"""
Somni Property Manager - Quote Models
Database models for quote generation and pricing
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    Text, ForeignKey, JSON, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID
from db.models import Base


class PricingTier(Base):
    """Pricing tiers for property management services"""
    __tablename__ = "pricing_tiers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Tier details
    tier_name = Column(String(100), nullable=False, unique=True)  # Starter, Professional, Enterprise
    tier_level = Column(Integer, nullable=False)  # 1, 2, 3 for ordering
    description = Column(Text)

    # Property Management SaaS Pricing
    price_per_unit_monthly = Column(Numeric(10, 2), nullable=False)  # $/unit/month
    min_units = Column(Integer, default=0)  # Minimum units for this tier
    max_units = Column(Integer)  # Maximum units (null = unlimited)

    # Base fees
    base_monthly_fee = Column(Numeric(10, 2), default=0)  # Flat monthly fee
    setup_fee = Column(Numeric(10, 2), default=0)  # One-time setup

    # Features included
    features_included = Column(JSON)  # List of features
    support_level = Column(String(50))  # Basic, Premium, White-Glove

    # Smart home services
    smart_home_basic_price = Column(Numeric(10, 2))  # $/unit/month
    smart_home_premium_price = Column(Numeric(10, 2))  # $/unit/month
    smart_home_enterprise_price = Column(Numeric(10, 2))  # $/unit/month

    # Status
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quotes = relationship("Quote", back_populates="pricing_tier")

    __table_args__ = (
        Index('idx_pricing_tiers_active', 'active'),
        Index('idx_pricing_tiers_level', 'tier_level'),
    )


class VendorPricing(Base):
    """Live pricing data from vendor websites (smart home hardware, integrations, etc.)"""
    __tablename__ = "vendor_pricing"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Vendor info
    vendor_name = Column(String(255), nullable=False)
    vendor_url = Column(String(500))
    product_name = Column(String(255), nullable=False)
    product_category = Column(String(100))  # smart-lock, thermostat, hub, software, etc.

    # Pricing
    unit_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='USD')
    pricing_model = Column(String(50))  # one-time, monthly, annual, per-unit

    # Metadata
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    source_url = Column(String(500))  # Specific product page
    notes = Column(Text)

    # Data quality
    confidence_score = Column(Numeric(3, 2))  # 0.0 - 1.0 confidence in pricing accuracy
    verified = Column(Boolean, default=False)  # Manually verified

    # Status
    active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_vendor_pricing_category', 'product_category'),
        Index('idx_vendor_pricing_active', 'active'),
        Index('idx_vendor_pricing_updated', 'last_updated'),
    )


class Quote(Base):
    """Customer quotes for property management services"""
    __tablename__ = "quotes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_number = Column(String(50), nullable=False, unique=True)  # Q-2026-001

    # Customer info
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255))
    customer_phone = Column(String(20))
    company_name = Column(String(255))

    # Property details
    total_units = Column(Integer, nullable=True, default=1)  # Nullable for hardware quotes
    property_count = Column(Integer, default=1)
    property_locations = Column(JSON)  # List of addresses/cities
    property_types = Column(JSON)  # residential, commercial, mixed

    # Selected pricing tier
    pricing_tier_id = Column(GUID, ForeignKey('pricing_tiers.id'))

    # ========================================================================
    # CLIENT & PROPERTY LINKAGE
    # ========================================================================
    # Link to client (who is this quote for?)
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='SET NULL'))
    # Link to specific property/building
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='SET NULL'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='SET NULL'))

    # Service selections
    include_smart_home = Column(Boolean, default=True)
    smart_home_penetration = Column(Numeric(5, 2), default=25.0)  # % of units with smart home
    smart_home_tier_distribution = Column(JSON)  # {basic: 70, premium: 25, enterprise: 5}

    # Calculated pricing (monthly)
    monthly_property_mgmt = Column(Numeric(10, 2))
    monthly_smart_home = Column(Numeric(10, 2))
    monthly_additional_fees = Column(Numeric(10, 2))
    monthly_total = Column(Numeric(10, 2), nullable=False)

    # Annual pricing
    annual_total = Column(Numeric(10, 2))

    # One-time costs
    setup_fees = Column(Numeric(10, 2), default=0)
    hardware_costs = Column(Numeric(10, 2), default=0)  # If selling hardware

    # Labor & Installation costs
    total_labor_cost = Column(Numeric(10, 2), default=0)  # Total labor from QuoteLaborItems
    total_materials_cost = Column(Numeric(10, 2), default=0)  # Total materials from labor items
    total_labor_hours = Column(Numeric(10, 2), default=0)  # Total estimated hours

    # Project timeline
    project_duration_days = Column(Integer)  # Estimated project duration in business days
    installation_start_date = Column(DateTime(timezone=True))  # Estimated start date
    installation_completion_date = Column(DateTime(timezone=True))  # Estimated completion date

    # Discounts
    discount_percentage = Column(Numeric(5, 2), default=0)
    discount_reason = Column(String(255))  # Early adopter, annual prepay, etc.
    discount_amount = Column(Numeric(10, 2), default=0)

    # Quote details
    valid_until = Column(DateTime(timezone=True))  # Quote expiration
    notes = Column(Text)
    terms_conditions = Column(Text)
    price_increase_disclaimers = Column(JSON)  # Array of potential reasons for price increases

    # Visual assets for immersive quote experience
    floor_plans = Column(JSON)  # Array of floor plan images/PDFs with metadata
    polycam_scans = Column(JSON)  # Array of Polycam 3D scan embeds
    implementation_photos = Column(JSON)  # Array of contractor's planned approach photos
    comparison_photos = Column(JSON)  # Array of before/after reference photos

    # Quote builder state (device placements, selections, workflow progress)
    builder_state = Column(JSON)  # Stores device_placements, selected_products, current_step, etc.

    # Status
    status = Column(String(50), default='draft')  # draft, sent, accepted, rejected, expired
    sent_at = Column(DateTime(timezone=True))
    accepted_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))

    # Conversion tracking
    converted_to_client_id = Column(GUID, ForeignKey('clients.id'))

    # Customer portal access
    customer_portal_token = Column(String(500))  # Secure token for customer portal access
    customer_portal_token_expires = Column(DateTime(timezone=True))  # Token expiration
    customer_portal_state = Column(JSON)  # Customer progress through portal (current_tab, tabs_viewed, etc.)

    # Invoice Ninja integration
    invoice_ninja_client_id = Column(String(255))  # Invoice Ninja client ID
    invoice_ninja_invoice_id = Column(String(255))  # Invoice Ninja invoice ID (when quote accepted)
    invoice_ninja_invoice_number = Column(String(100))  # Invoice number from Invoice Ninja

    # Customer acceptance fields
    customer_signature = Column(Text)  # Base64 encoded signature image
    acceptance_notes = Column(Text)  # Notes from customer at acceptance

    # Service location (for quotes not linked to a specific property)
    service_address = Column(Text)  # Service/installation address

    # Total amount (convenience field for quick access)
    total_amount = Column(Numeric(12, 2))  # Grand total including all costs

    # Metadata
    created_by = Column(String(255))  # User who created quote
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    pricing_tier = relationship("PricingTier", back_populates="quotes")

    # Client & property relationships
    client = relationship("Client", foreign_keys=[client_id], backref="quotes")
    property = relationship("Property", foreign_keys=[property_id], backref="quotes")
    building = relationship("Building", foreign_keys=[building_id], backref="quotes")
    converted_client = relationship("Client", foreign_keys=[converted_to_client_id], backref="converted_quotes")

    # Quote details
    line_items = relationship("QuoteLineItem", back_populates="quote", cascade="all, delete-orphan")
    product_options = relationship("QuoteProductOption", back_populates="quote", cascade="all, delete-orphan")
    comments = relationship("QuoteComment", back_populates="quote", cascade="all, delete-orphan")
    customer_selection = relationship("QuoteCustomerSelection", back_populates="quote", cascade="all, delete-orphan", uselist=False)

    # Project phase relationships
    project_phases = relationship("ProjectPhase", back_populates="quote", cascade="all, delete-orphan")
    deposits = relationship("ProjectDeposit", back_populates="quote", cascade="all, delete-orphan")
    project_timeline = relationship("ProjectTimeline", back_populates="quote", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'sent', 'accepted', 'rejected', 'expired')",
            name='valid_quote_status'
        ),
        Index('idx_quotes_status', 'status'),
        Index('idx_quotes_customer_email', 'customer_email'),
        Index('idx_quotes_created_at', 'created_at'),
        Index('idx_quotes_number', 'quote_number'),
        Index('idx_quotes_client_id', 'client_id'),
        Index('idx_quotes_property_id', 'property_id'),
        Index('idx_quotes_building_id', 'building_id'),
        Index('idx_quotes_converted_to_client_id', 'converted_to_client_id'),
    )


class QuoteLineItem(Base):
    """Individual line items in a quote"""
    __tablename__ = "quote_line_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)

    # Line item details
    line_number = Column(Integer, nullable=False)
    category = Column(String(100))  # Property Mgmt, Smart Home, Hardware, Setup, etc.
    description = Column(Text, nullable=False)

    # Pricing
    quantity = Column(Numeric(10, 2), nullable=False)  # Units, devices, etc.
    unit_price = Column(Numeric(10, 2), nullable=False)
    unit_type = Column(String(50))  # per unit/month, one-time, etc.

    subtotal = Column(Numeric(10, 2), nullable=False)

    # Metadata
    vendor_pricing_id = Column(GUID, ForeignKey('vendor_pricing.id'))  # If from vendor data
    notes = Column(Text)

    # Relationships
    quote = relationship("Quote", back_populates="line_items")

    __table_args__ = (
        Index('idx_quote_line_items_quote_id', 'quote_id'),
    )


class QuoteTemplate(Base):
    """Reusable quote templates for different scenarios"""
    __tablename__ = "quote_templates"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    template_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)

    # Template configuration
    default_pricing_tier_id = Column(GUID, ForeignKey('pricing_tiers.id'))
    default_terms = Column(Text)
    default_validity_days = Column(Integer, default=30)

    # Default line items (JSON)
    default_line_items = Column(JSON)

    # Template metadata
    use_count = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_quote_templates_active', 'active'),
    )


class QuoteProductOption(Base):
    """Product tier options (Economy/Standard/Premium) for quote line items"""
    __tablename__ = "quote_product_options"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)
    product_category = Column(String(100), nullable=False)  # smart_locks, thermostats, hub, etc.

    # Economy tier
    economy_product_name = Column(String(255))
    economy_unit_price = Column(Numeric(10, 2))
    economy_vendor_pricing_id = Column(GUID, ForeignKey('vendor_pricing.id', ondelete='SET NULL'))
    economy_description = Column(Text)

    # Standard tier
    standard_product_name = Column(String(255))
    standard_unit_price = Column(Numeric(10, 2))
    standard_vendor_pricing_id = Column(GUID, ForeignKey('vendor_pricing.id', ondelete='SET NULL'))
    standard_description = Column(Text)

    # Premium tier
    premium_product_name = Column(String(255))
    premium_unit_price = Column(Numeric(10, 2))
    premium_vendor_pricing_id = Column(GUID, ForeignKey('vendor_pricing.id', ondelete='SET NULL'))
    premium_description = Column(Text)

    quantity = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="product_options")

    __table_args__ = (
        Index('idx_quote_product_options_quote_id', 'quote_id'),
        Index('idx_quote_product_options_category', 'product_category'),
    )


class QuoteComment(Base):
    """Comments and questions on quotes - customer and internal"""
    __tablename__ = "quote_comments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)
    line_item_id = Column(GUID, ForeignKey('quote_line_items.id', ondelete='SET NULL'))
    parent_comment_id = Column(GUID, ForeignKey('quote_comments.id', ondelete='CASCADE'))

    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(50))  # question, concern, request, response, internal

    # Attribution
    created_by = Column(String(255))  # Admin username or 'customer'
    created_by_email = Column(String(255))  # Customer email
    is_internal = Column(Boolean, default=False)  # Hidden from customer

    # Metadata
    attachments = Column(JSON)  # File references
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="comments")
    replies = relationship("QuoteComment", backref="parent", remote_side=[id])

    __table_args__ = (
        Index('idx_quote_comments_quote_id', 'quote_id'),
        Index('idx_quote_comments_parent', 'parent_comment_id'),
        Index('idx_quote_comments_is_internal', 'is_internal'),
        Index('idx_quote_comments_created_at', 'created_at'),
    )


class QuoteCustomerSelection(Base):
    """Customer's product tier selections and approval"""
    __tablename__ = "quote_customer_selections"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)

    selected_tier = Column(String(50))  # economy, standard, premium, custom

    # Custom mix-and-match selections
    custom_selections = Column(JSON)  # {"smart_locks": "premium", "thermostats": "standard"}

    total_hardware_cost = Column(Numeric(10, 2))
    total_monthly_cost = Column(Numeric(10, 2))

    customer_notes = Column(Text)
    approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="customer_selection")

    __table_args__ = (
        Index('idx_quote_customer_selections_quote_id', 'quote_id'),
        Index('idx_quote_customer_selections_approved', 'approved'),
    )


# ============================================================================
# LABOR PRICING MODELS
# ============================================================================

class LaborTemplate(Base):
    """
    Predefined labor templates for common installation/configuration tasks
    Enables intelligent labor estimation based on device types and quantities
    """
    __tablename__ = "labor_templates"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Template identification
    template_name = Column(String(255), nullable=False, unique=True)  # "Smart Lock Installation", "Hub Configuration"
    template_code = Column(String(50), unique=True)  # "INSTALL_LOCK", "CONFIG_HUB"
    category = Column(String(100), nullable=False)  # Installation, Configuration, Testing, Training, etc.

    # Description
    description = Column(Text, nullable=False)  # What work will be performed
    detailed_scope = Column(Text)  # Detailed scope of work

    # Pricing
    base_hours = Column(Numeric(10, 2), nullable=False)  # Base hours for the task
    hourly_rate = Column(Numeric(10, 2), nullable=False)  # Labor rate ($/hr)

    # Scaling factors (for calculating based on quantity)
    additional_hours_per_unit = Column(Numeric(10, 2), default=0)  # Extra hours per additional device
    efficiency_factor = Column(Numeric(5, 2), default=1.0)  # Efficiency multiplier (0.5 = faster, 1.5 = slower)

    # Device/Product associations
    applicable_product_categories = Column(JSON)  # ["smart_lock", "thermostat"] - which products trigger this labor
    applicable_domains = Column(JSON)  # ["access_control", "climate"] - which domains need this

    # Requirements
    required_skills = Column(JSON)  # ["electrical", "networking", "programming"]
    required_certifications = Column(JSON)  # ["electrician_license", "low_voltage_cert"]

    # Materials
    typical_materials = Column(JSON)  # [{"name": "CAT6 cable", "unit": "ft", "qty_per_unit": 50}]

    # Conditions
    prerequisites = Column(JSON)  # ["network_configured", "power_available"]
    notes = Column(Text)

    # Auto-inclusion rules
    auto_include = Column(Boolean, default=False)  # Automatically add to quote when conditions met
    auto_include_conditions = Column(JSON)  # Conditions for auto-inclusion

    # Status
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_labor_templates_category', 'category'),
        Index('idx_labor_templates_active', 'active'),
        Index('idx_labor_templates_code', 'template_code'),
    )


class QuoteLaborItem(Base):
    """
    Labor items added to a specific quote
    Calculated or manually added labor costs with detailed breakdown
    """
    __tablename__ = "quote_labor_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)
    labor_template_id = Column(GUID, ForeignKey('labor_templates.id', ondelete='SET NULL'))

    # Labor details
    line_number = Column(Integer, nullable=False)
    category = Column(String(100), nullable=False)  # Installation, Configuration, Testing, Training
    task_name = Column(String(255), nullable=False)  # "Install 15 smart locks"
    description = Column(Text, nullable=False)  # Detailed explanation of work
    scope_of_work = Column(Text)  # Line-by-line scope

    # Pricing calculation
    estimated_hours = Column(Numeric(10, 2), nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=False)
    labor_subtotal = Column(Numeric(10, 2), nullable=False)  # hours * rate

    # Quantity/scaling
    quantity = Column(Numeric(10, 2), default=1)  # Number of units this labor applies to
    unit_type = Column(String(50))  # "per device", "per building", "per property"

    # Associated products (what devices/products is this labor for?)
    associated_product_ids = Column(JSON)  # Links to product options or line items
    associated_device_count = Column(Integer, default=0)  # Number of devices

    # Materials needed
    materials_needed = Column(JSON)  # [{"name": "CAT6 cable", "qty": 500, "unit": "ft", "cost": 150}]
    materials_cost = Column(Numeric(10, 2), default=0)  # Total materials cost

    # Total (labor + materials)
    total_cost = Column(Numeric(10, 2), nullable=False)

    # Status
    is_auto_calculated = Column(Boolean, default=False)  # Was this auto-calculated or manual?
    is_optional = Column(Boolean, default=False)  # Can customer opt-out?
    requires_approval = Column(Boolean, default=False)  # Needs special approval?

    # Scheduling
    estimated_start_date = Column(DateTime(timezone=True))
    estimated_completion_date = Column(DateTime(timezone=True))
    duration_days = Column(Integer)  # Estimated project duration

    # Notes
    internal_notes = Column(Text)  # Internal notes for team
    customer_notes = Column(Text)  # Notes visible to customer

    display_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ========================================================================
    # CONTRACTOR WORK TRACKING FIELDS (for somni-employee mobile app)
    # ========================================================================
    # Contractor assignment
    assigned_contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='SET NULL'))
    contractor_assigned_at = Column(DateTime(timezone=True))
    contractor_assigned_by = Column(String(255))

    # Work status tracking
    work_status = Column(String(50), default='pending')  # pending, assigned, in_progress, completed, on_hold, cancelled, needs_review
    work_started_at = Column(DateTime(timezone=True))
    work_completed_at = Column(DateTime(timezone=True))

    # Actual time tracking
    actual_hours = Column(Numeric(10, 2))
    actual_labor_cost = Column(Numeric(10, 2))
    actual_materials_cost = Column(Numeric(10, 2))
    actual_total_cost = Column(Numeric(10, 2))

    # Variance tracking
    hours_variance = Column(Numeric(10, 2))
    cost_variance = Column(Numeric(10, 2))

    # Customer approval
    requires_customer_approval = Column(Boolean, default=False)
    customer_approved = Column(Boolean)
    customer_approved_at = Column(DateTime(timezone=True))
    customer_approval_notes = Column(Text)

    # Quality control
    qc_passed = Column(Boolean)
    qc_performed_by = Column(String(255))
    qc_performed_at = Column(DateTime(timezone=True))
    qc_notes = Column(Text)

    # Location tracking
    work_location_coords = Column(JSON)  # {"lat": x, "lng": y}
    work_location_address = Column(Text)

    # Equipment/tools used
    equipment_used = Column(JSON)

    # Additional metadata
    weather_conditions = Column(Text)
    access_notes = Column(Text)
    safety_notes = Column(Text)

    # Relationships
    quote = relationship("Quote", backref="labor_items")
    labor_template = relationship("LaborTemplate")
    assigned_contractor = relationship("Contractor", foreign_keys=[assigned_contractor_id])

    # Contractor labor documentation relationships (from models_contractor_labor.py)
    photos = relationship("QuoteLaborItemPhoto", back_populates="labor_item", cascade="all, delete-orphan")
    notes = relationship("QuoteLaborItemNote", back_populates="labor_item", cascade="all, delete-orphan")
    time_entries = relationship("QuoteLaborTimeEntry", back_populates="labor_item", cascade="all, delete-orphan")
    materials_used = relationship("QuoteLaborMaterialUsed", back_populates="labor_item", cascade="all, delete-orphan")
    history = relationship("QuoteLaborItemHistory", back_populates="labor_item", cascade="all, delete-orphan")
    before_after_pairs = relationship("QuoteLaborBeforeAfterPair", back_populates="labor_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_quote_labor_items_quote_id', 'quote_id'),
        Index('idx_quote_labor_items_category', 'category'),
        Index('idx_quote_labor_items_template_id', 'labor_template_id'),
        Index('idx_quote_labor_items_contractor_id', 'assigned_contractor_id'),
        Index('idx_quote_labor_items_work_status', 'work_status'),
        CheckConstraint(
            "work_status IN ('pending', 'assigned', 'in_progress', 'completed', 'on_hold', 'cancelled', 'needs_review')",
            name='valid_work_status'
        ),
    )


class LaborMaterial(Base):
    """
    Materials catalog for labor tasks
    Tracks materials needed for various installation/configuration tasks
    """
    __tablename__ = "labor_materials"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Material identification
    material_name = Column(String(255), nullable=False)
    material_code = Column(String(50), unique=True)
    category = Column(String(100))  # Cable, Mounting, Electrical, Networking, etc.

    # Description
    description = Column(Text)
    specifications = Column(Text)

    # Pricing
    unit_cost = Column(Numeric(10, 2), nullable=False)
    unit_type = Column(String(50), nullable=False)  # ft, ea, box, roll, etc.

    # Vendor info
    vendor_name = Column(String(255))
    vendor_sku = Column(String(100))
    vendor_url = Column(String(500))

    # Usage estimates
    typical_quantity_per_install = Column(Numeric(10, 2))  # Typical quantity used
    wastage_factor = Column(Numeric(5, 2), default=1.1)  # Account for waste (10% default)

    # Stock management
    stock_quantity = Column(Numeric(10, 2), default=0)
    reorder_threshold = Column(Numeric(10, 2), default=0)

    # Status
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_labor_materials_category', 'category'),
        Index('idx_labor_materials_active', 'active'),
    )
