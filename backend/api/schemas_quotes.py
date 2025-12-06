"""
Somni Property Manager - Quote Schemas
Pydantic models for quote generation and pricing
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# ============================================================================
# PRICING TIER SCHEMAS
# ============================================================================

class PricingTierBase(BaseModel):
    tier_name: str = Field(..., max_length=100)
    tier_level: int = Field(..., ge=1, le=10)
    description: Optional[str] = None

    price_per_unit_monthly: Decimal = Field(..., ge=0)
    min_units: int = Field(default=0, ge=0)
    max_units: Optional[int] = Field(None, ge=0)

    base_monthly_fee: Decimal = Field(default=0, ge=0)
    setup_fee: Decimal = Field(default=0, ge=0)

    features_included: Optional[List[str]] = None
    support_level: Optional[str] = None

    smart_home_basic_price: Optional[Decimal] = Field(None, ge=0)
    smart_home_premium_price: Optional[Decimal] = Field(None, ge=0)
    smart_home_enterprise_price: Optional[Decimal] = Field(None, ge=0)

    active: bool = True


class PricingTierCreate(PricingTierBase):
    pass


class PricingTierUpdate(BaseModel):
    tier_name: Optional[str] = Field(None, max_length=100)
    tier_level: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = None

    price_per_unit_monthly: Optional[Decimal] = Field(None, ge=0)
    min_units: Optional[int] = Field(None, ge=0)
    max_units: Optional[int] = Field(None, ge=0)

    base_monthly_fee: Optional[Decimal] = Field(None, ge=0)
    setup_fee: Optional[Decimal] = Field(None, ge=0)

    features_included: Optional[List[str]] = None
    support_level: Optional[str] = None

    smart_home_basic_price: Optional[Decimal] = Field(None, ge=0)
    smart_home_premium_price: Optional[Decimal] = Field(None, ge=0)
    smart_home_enterprise_price: Optional[Decimal] = Field(None, ge=0)

    active: Optional[bool] = None


class PricingTier(PricingTierBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# VENDOR PRICING SCHEMAS
# ============================================================================

class VendorPricingBase(BaseModel):
    vendor_name: str = Field(..., max_length=255)
    vendor_url: Optional[str] = Field(None, max_length=500)
    product_name: str = Field(..., max_length=255)
    product_category: Optional[str] = Field(None, max_length=100)

    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field(default='USD', max_length=3)
    pricing_model: Optional[str] = Field(None, max_length=50)

    source_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None

    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    verified: bool = False
    active: bool = True


class VendorPricingCreate(VendorPricingBase):
    pass


class VendorPricingUpdate(BaseModel):
    vendor_name: Optional[str] = Field(None, max_length=255)
    vendor_url: Optional[str] = Field(None, max_length=500)
    product_name: Optional[str] = Field(None, max_length=255)
    product_category: Optional[str] = Field(None, max_length=100)

    unit_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    pricing_model: Optional[str] = Field(None, max_length=50)

    source_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None

    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    verified: Optional[bool] = None
    active: Optional[bool] = None


class VendorPricing(VendorPricingBase):
    id: UUID
    scraped_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QUOTE SCHEMAS
# ============================================================================

class QuoteLineItemBase(BaseModel):
    line_number: int = Field(..., ge=1)
    category: Optional[str] = Field(None, max_length=100)
    description: str

    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    unit_type: Optional[str] = Field(None, max_length=50)

    subtotal: Decimal = Field(..., ge=0)

    vendor_pricing_id: Optional[UUID] = None
    notes: Optional[str] = None


class QuoteLineItemCreate(QuoteLineItemBase):
    pass


class QuoteLineItem(QuoteLineItemBase):
    id: UUID
    quote_id: UUID

    class Config:
        from_attributes = True


class QuoteBase(BaseModel):
    customer_name: str = Field(..., max_length=255)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    company_name: Optional[str] = Field(None, max_length=255)

    # Client linkage
    client_id: Optional[UUID] = None  # Link quote to existing client
    property_id: Optional[UUID] = None  # Link to specific property
    building_id: Optional[UUID] = None  # Link to specific building

    total_units: int = Field(default=1, gt=0)  # Default to 1 for hardware quotes
    property_count: int = Field(default=1, ge=1)
    property_locations: Optional[List[str]] = None
    property_types: Optional[List[str]] = None

    pricing_tier_id: Optional[UUID] = None

    include_smart_home: bool = True
    smart_home_penetration: Decimal = Field(default=25.0, ge=0, le=100)
    smart_home_tier_distribution: Optional[Dict[str, Decimal]] = Field(
        default={"basic": 70, "premium": 25, "enterprise": 5}
    )

    discount_percentage: Decimal = Field(default=0, ge=0, le=100)
    discount_reason: Optional[str] = Field(None, max_length=255)

    notes: Optional[str] = None
    terms_conditions: Optional[str] = None

    valid_until: Optional[datetime] = None

    # Visual assets for immersive quotes
    floor_plans: Optional[List[Dict[str, Any]]] = None

    # Quote builder state (device placements, selections, workflow progress)
    builder_state: Optional[Dict[str, Any]] = None

    # Customer portal state (customer progress through portal)
    customer_portal_state: Optional[Dict[str, Any]] = None


class QuoteCreate(QuoteBase):
    """Create a new quote - calculations will be done server-side"""
    pass


class QuoteUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    company_name: Optional[str] = Field(None, max_length=255)

    total_units: Optional[int] = Field(None, gt=0)  # Optional for hardware quotes
    property_count: Optional[int] = Field(None, ge=1)
    property_locations: Optional[List[str]] = None
    property_types: Optional[List[str]] = None

    pricing_tier_id: Optional[UUID] = None

    include_smart_home: Optional[bool] = None
    smart_home_penetration: Optional[Decimal] = Field(None, ge=0, le=100)
    smart_home_tier_distribution: Optional[Dict[str, Decimal]] = None

    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_reason: Optional[str] = Field(None, max_length=255)

    notes: Optional[str] = None
    terms_conditions: Optional[str] = None

    status: Optional[str] = Field(None, pattern="^(draft|sent|accepted|rejected|expired)$")
    valid_until: Optional[datetime] = None

    # Visual assets for immersive quotes
    floor_plans: Optional[List[Dict[str, Any]]] = None

    # Quote builder state (device placements, selections, workflow progress)
    builder_state: Optional[Dict[str, Any]] = None

    # Customer portal state (customer progress through portal)
    customer_portal_state: Optional[Dict[str, Any]] = None


class Quote(QuoteBase):
    id: UUID
    quote_number: str

    monthly_property_mgmt: Optional[Decimal] = None
    monthly_smart_home: Optional[Decimal] = None
    monthly_additional_fees: Optional[Decimal] = None
    monthly_total: Optional[Decimal] = None

    annual_total: Optional[Decimal] = None

    setup_fees: Optional[Decimal] = None
    hardware_costs: Optional[Decimal] = None

    discount_amount: Optional[Decimal] = None

    status: str
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None

    converted_to_client_id: Optional[UUID] = None

    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Included relationships
    line_items: List[QuoteLineItem] = []

    class Config:
        from_attributes = True


class QuoteCalculationRequest(BaseModel):
    """Request to calculate quote pricing without saving"""
    total_units: int = Field(default=1, gt=0)  # Default to 1 for hardware quotes
    pricing_tier_id: Optional[UUID] = None
    include_smart_home: bool = True
    smart_home_penetration: Decimal = Field(default=25.0, ge=0, le=100)
    smart_home_tier_distribution: Optional[Dict[str, Decimal]] = Field(
        default={"basic": 70, "premium": 25, "enterprise": 5}
    )
    discount_percentage: Decimal = Field(default=0, ge=0, le=100)


class QuoteCalculationResponse(BaseModel):
    """Calculated quote pricing breakdown"""
    total_units: int

    # Monthly breakdown
    monthly_property_mgmt: Decimal
    monthly_smart_home: Decimal
    monthly_additional_fees: Decimal
    monthly_subtotal: Decimal
    monthly_discount: Decimal
    monthly_total: Decimal

    # Annual
    annual_total: Decimal

    # One-time
    setup_fees: Decimal

    # Per-unit costs
    cost_per_unit_monthly: Decimal

    # Smart home breakdown
    smart_home_units: int
    smart_home_basic_units: int
    smart_home_premium_units: int
    smart_home_enterprise_units: int

    # Pricing tier used
    pricing_tier: Optional[PricingTier] = None


class QuoteSummaryStats(BaseModel):
    """Summary statistics for quotes"""
    total_quotes: int
    quotes_by_status: Dict[str, int]
    total_value_monthly: Decimal
    total_value_annual: Decimal
    average_units_per_quote: Decimal
    conversion_rate: Decimal


# ============================================================================
# LIST RESPONSE SCHEMAS
# ============================================================================

class PricingTierListResponse(BaseModel):
    items: List[PricingTier]
    total: int
    skip: int
    limit: int


class VendorPricingListResponse(BaseModel):
    items: List[VendorPricing]
    total: int
    skip: int
    limit: int


class QuoteListResponse(BaseModel):
    items: List[Quote]
    total: int
    skip: int
    limit: int


# ============================================================================
# QUOTE PRODUCT OPTIONS SCHEMAS
# ============================================================================

class QuoteProductOptionBase(BaseModel):
    product_category: str = Field(..., max_length=100)

    # Economy tier
    economy_product_name: Optional[str] = Field(None, max_length=255)
    economy_unit_price: Optional[Decimal] = Field(None, ge=0)
    economy_vendor_pricing_id: Optional[UUID] = None
    economy_description: Optional[str] = None

    # Standard tier
    standard_product_name: Optional[str] = Field(None, max_length=255)
    standard_unit_price: Optional[Decimal] = Field(None, ge=0)
    standard_vendor_pricing_id: Optional[UUID] = None
    standard_description: Optional[str] = None

    # Premium tier
    premium_product_name: Optional[str] = Field(None, max_length=255)
    premium_unit_price: Optional[Decimal] = Field(None, ge=0)
    premium_vendor_pricing_id: Optional[UUID] = None
    premium_description: Optional[str] = None

    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = None
    display_order: int = Field(default=0, ge=0)


class QuoteProductOptionCreate(QuoteProductOptionBase):
    quote_id: UUID


class QuoteProductOptionUpdate(BaseModel):
    product_category: Optional[str] = Field(None, max_length=100)

    economy_product_name: Optional[str] = Field(None, max_length=255)
    economy_unit_price: Optional[Decimal] = Field(None, ge=0)
    economy_vendor_pricing_id: Optional[UUID] = None
    economy_description: Optional[str] = None

    standard_product_name: Optional[str] = Field(None, max_length=255)
    standard_unit_price: Optional[Decimal] = Field(None, ge=0)
    standard_vendor_pricing_id: Optional[UUID] = None
    standard_description: Optional[str] = None

    premium_product_name: Optional[str] = Field(None, max_length=255)
    premium_unit_price: Optional[Decimal] = Field(None, ge=0)
    premium_vendor_pricing_id: Optional[UUID] = None
    premium_description: Optional[str] = None

    quantity: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)


class QuoteProductOption(QuoteProductOptionBase):
    id: UUID
    quote_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# QUOTE COMMENTS SCHEMAS
# ============================================================================

class QuoteCommentBase(BaseModel):
    comment_text: str
    comment_type: Optional[str] = Field(None, max_length=50)
    line_item_id: Optional[UUID] = None
    parent_comment_id: Optional[UUID] = None
    is_internal: bool = False
    attachments: Optional[List[Dict[str, Any]]] = None


class QuoteCommentCreate(QuoteCommentBase):
    quote_id: UUID
    created_by: Optional[str] = None
    created_by_email: Optional[EmailStr] = None


class QuoteCommentUpdate(BaseModel):
    comment_text: Optional[str] = None
    comment_type: Optional[str] = Field(None, max_length=50)
    resolved: Optional[bool] = None
    is_internal: Optional[bool] = None


class QuoteComment(QuoteCommentBase):
    id: UUID
    quote_id: UUID
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Nested replies
    replies: List['QuoteComment'] = []

    class Config:
        from_attributes = True


# ============================================================================
# QUOTE CUSTOMER SELECTION SCHEMAS
# ============================================================================

class QuoteCustomerSelectionBase(BaseModel):
    selected_tier: Optional[str] = Field(None, max_length=50)
    custom_selections: Optional[Dict[str, str]] = None
    customer_notes: Optional[str] = None


class QuoteCustomerSelectionCreate(QuoteCustomerSelectionBase):
    quote_id: UUID


class QuoteCustomerSelectionUpdate(QuoteCustomerSelectionBase):
    total_hardware_cost: Optional[Decimal] = Field(None, ge=0)
    total_monthly_cost: Optional[Decimal] = Field(None, ge=0)
    approved: Optional[bool] = None


class QuoteCustomerSelection(QuoteCustomerSelectionBase):
    id: UUID
    quote_id: UUID
    total_hardware_cost: Optional[Decimal] = None
    total_monthly_cost: Optional[Decimal] = None
    approved: bool
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CUSTOMER PORTAL SCHEMAS
# ============================================================================

class CustomerPortalLinkResponse(BaseModel):
    """Response when generating customer portal link"""
    customer_portal_url: str
    token: str
    expires_at: datetime


class QuoteApprovalRequest(BaseModel):
    """Customer approves quote via portal"""
    approved: bool
    approval_notes: Optional[str] = None


class QuoteRejectionRequest(BaseModel):
    """Customer rejects quote via portal"""
    rejection_reason: str
    alternative_suggestions: Optional[str] = None


# ============================================================================
# LABOR PRICING SCHEMAS
# ============================================================================

class LaborTemplateBase(BaseModel):
    template_name: str = Field(..., max_length=255)
    template_code: Optional[str] = Field(None, max_length=50)
    category: str = Field(..., max_length=100)

    description: str
    detailed_scope: Optional[str] = None

    base_hours: Decimal = Field(..., ge=0)
    hourly_rate: Decimal = Field(..., ge=0)

    additional_hours_per_unit: Decimal = Field(default=0, ge=0)
    efficiency_factor: Decimal = Field(default=1.0, gt=0)

    applicable_product_categories: Optional[List[str]] = None
    applicable_domains: Optional[List[str]] = None

    required_skills: Optional[List[str]] = None
    required_certifications: Optional[List[str]] = None

    typical_materials: Optional[List[Dict[str, Any]]] = None
    prerequisites: Optional[List[str]] = None
    notes: Optional[str] = None

    auto_include: bool = False
    auto_include_conditions: Optional[Dict[str, Any]] = None

    active: bool = True


class LaborTemplateCreate(LaborTemplateBase):
    pass


class LaborTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, max_length=255)
    template_code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)

    description: Optional[str] = None
    detailed_scope: Optional[str] = None

    base_hours: Optional[Decimal] = Field(None, ge=0)
    hourly_rate: Optional[Decimal] = Field(None, ge=0)

    additional_hours_per_unit: Optional[Decimal] = Field(None, ge=0)
    efficiency_factor: Optional[Decimal] = Field(None, gt=0)

    applicable_product_categories: Optional[List[str]] = None
    applicable_domains: Optional[List[str]] = None

    required_skills: Optional[List[str]] = None
    required_certifications: Optional[List[str]] = None

    typical_materials: Optional[List[Dict[str, Any]]] = None
    prerequisites: Optional[List[str]] = None
    notes: Optional[str] = None

    auto_include: Optional[bool] = None
    auto_include_conditions: Optional[Dict[str, Any]] = None

    active: Optional[bool] = None


class LaborTemplate(LaborTemplateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteLaborItemBase(BaseModel):
    line_number: int = Field(..., ge=1)
    category: str = Field(..., max_length=100)
    task_name: str = Field(..., max_length=255)
    description: str
    scope_of_work: Optional[str] = None

    estimated_hours: Decimal = Field(..., gt=0)
    hourly_rate: Decimal = Field(..., ge=0)
    labor_subtotal: Decimal = Field(..., ge=0)

    quantity: Decimal = Field(default=1, gt=0)
    unit_type: Optional[str] = Field(None, max_length=50)

    associated_product_ids: Optional[List[str]] = None
    associated_device_count: int = Field(default=0, ge=0)

    materials_needed: Optional[List[Dict[str, Any]]] = None
    materials_cost: Decimal = Field(default=0, ge=0)

    total_cost: Decimal = Field(..., ge=0)

    is_auto_calculated: bool = False
    is_optional: bool = False
    requires_approval: bool = False

    estimated_start_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None
    duration_days: Optional[int] = Field(None, ge=0)

    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None

    display_order: int = Field(default=0, ge=0)


class QuoteLaborItemCreate(QuoteLaborItemBase):
    quote_id: UUID
    labor_template_id: Optional[UUID] = None


class QuoteLaborItemUpdate(BaseModel):
    line_number: Optional[int] = Field(None, ge=1)
    category: Optional[str] = Field(None, max_length=100)
    task_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    scope_of_work: Optional[str] = None

    estimated_hours: Optional[Decimal] = Field(None, gt=0)
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    labor_subtotal: Optional[Decimal] = Field(None, ge=0)

    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_type: Optional[str] = Field(None, max_length=50)

    associated_product_ids: Optional[List[str]] = None
    associated_device_count: Optional[int] = Field(None, ge=0)

    materials_needed: Optional[List[Dict[str, Any]]] = None
    materials_cost: Optional[Decimal] = Field(None, ge=0)

    total_cost: Optional[Decimal] = Field(None, ge=0)

    is_auto_calculated: Optional[bool] = None
    is_optional: Optional[bool] = None
    requires_approval: Optional[bool] = None

    estimated_start_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None
    duration_days: Optional[int] = Field(None, ge=0)

    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None

    display_order: Optional[int] = Field(None, ge=0)


class QuoteLaborItem(QuoteLaborItemBase):
    id: UUID
    quote_id: UUID
    labor_template_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LaborMaterialBase(BaseModel):
    material_name: str = Field(..., max_length=255)
    material_code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)

    description: Optional[str] = None
    specifications: Optional[str] = None

    unit_cost: Decimal = Field(..., ge=0)
    unit_type: str = Field(..., max_length=50)

    vendor_name: Optional[str] = Field(None, max_length=255)
    vendor_sku: Optional[str] = Field(None, max_length=100)
    vendor_url: Optional[str] = Field(None, max_length=500)

    typical_quantity_per_install: Optional[Decimal] = Field(None, ge=0)
    wastage_factor: Decimal = Field(default=1.1, gt=0)

    stock_quantity: Decimal = Field(default=0, ge=0)
    reorder_threshold: Decimal = Field(default=0, ge=0)

    active: bool = True


class LaborMaterialCreate(LaborMaterialBase):
    pass


class LaborMaterialUpdate(BaseModel):
    material_name: Optional[str] = Field(None, max_length=255)
    material_code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)

    description: Optional[str] = None
    specifications: Optional[str] = None

    unit_cost: Optional[Decimal] = Field(None, ge=0)
    unit_type: Optional[str] = Field(None, max_length=50)

    vendor_name: Optional[str] = Field(None, max_length=255)
    vendor_sku: Optional[str] = Field(None, max_length=100)
    vendor_url: Optional[str] = Field(None, max_length=500)

    typical_quantity_per_install: Optional[Decimal] = Field(None, ge=0)
    wastage_factor: Optional[Decimal] = Field(None, gt=0)

    stock_quantity: Optional[Decimal] = Field(None, ge=0)
    reorder_threshold: Optional[Decimal] = Field(None, ge=0)

    active: Optional[bool] = None


class LaborMaterial(LaborMaterialBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LaborEstimationRequest(BaseModel):
    """Request to estimate labor based on selected products"""
    quote_id: UUID
    product_selections: List[Dict[str, Any]]  # Product IDs and quantities
    include_materials: bool = True
    labor_rate_override: Optional[Decimal] = None


class LaborEstimationResponse(BaseModel):
    """Response with estimated labor items"""
    labor_items: List[QuoteLaborItem]
    total_labor_hours: Decimal
    total_labor_cost: Decimal
    total_materials_cost: Decimal
    total_cost: Decimal
    estimated_duration_days: int


# Update forward references
QuoteComment.model_rebuild()
