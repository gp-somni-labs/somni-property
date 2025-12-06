"""
Somni Property Manager - Pydantic Schemas
Request/response models for API validation
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_serializer, field_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


# ============================================================================
# PROPERTY SCHEMAS
# ============================================================================

class PropertyBase(BaseModel):
    name: str = Field(..., max_length=255)
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=50)
    zip_code: str = Field(..., max_length=20)
    country: str = Field(default="USA", max_length=100)
    property_type: str = Field(..., pattern="^(residential|commercial|mixed-use)$")
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = Field(None, max_length=20)
    ha_instance_id: Optional[str] = Field(None, max_length=100)
    tailscale_ip: Optional[str] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    property_type: Optional[str] = Field(None, pattern="^(residential|commercial|mixed-use)$")
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = Field(None, max_length=20)
    ha_instance_id: Optional[str] = Field(None, max_length=100)
    tailscale_ip: Optional[str] = None


class Property(PropertyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# BUILDING SCHEMAS
# ============================================================================

class BuildingBase(BaseModel):
    property_id: UUID
    name: str = Field(..., max_length=255)
    floors: int = Field(default=1, ge=1)
    total_units: int = Field(default=0, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    square_feet: Optional[int] = Field(None, ge=0)
    has_central_hvac: bool = False
    has_central_water: bool = False
    has_elevator: bool = False
    has_parking: bool = False
    parking_spaces: int = Field(default=0, ge=0)
    mqtt_topic_prefix: Optional[str] = Field(None, max_length=255)


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    floors: Optional[int] = Field(None, ge=1)
    total_units: Optional[int] = Field(None, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    square_feet: Optional[int] = Field(None, ge=0)
    has_central_hvac: Optional[bool] = None
    has_central_water: Optional[bool] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    parking_spaces: Optional[int] = Field(None, ge=0)
    mqtt_topic_prefix: Optional[str] = Field(None, max_length=255)


class Building(BuildingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# UNIT SCHEMAS
# ============================================================================

class UnitBase(BaseModel):
    building_id: UUID
    unit_number: str = Field(..., max_length=50)
    floor: int = Field(default=1, ge=1)
    bedrooms: Decimal = Field(default=0, ge=0)
    bathrooms: Decimal = Field(default=1, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    monthly_rent: Optional[Decimal] = None
    security_deposit: Optional[Decimal] = None
    status: str = Field(default="vacant", pattern="^(vacant|occupied|maintenance|unavailable)$")
    available_date: Optional[date] = None
    has_washer_dryer: bool = False
    has_dishwasher: bool = False
    has_ac: bool = False
    has_balcony: bool = False
    smart_lock_entity_id: Optional[str] = Field(None, max_length=255)
    thermostat_entity_id: Optional[str] = Field(None, max_length=255)
    energy_sensor_entity_id: Optional[str] = Field(None, max_length=255)
    water_sensor_entity_id: Optional[str] = Field(None, max_length=255)
    occupancy_sensor_entity_id: Optional[str] = Field(None, max_length=255)


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = Field(None, max_length=50)
    floor: Optional[int] = Field(None, ge=1)
    bedrooms: Optional[Decimal] = Field(None, ge=0)
    bathrooms: Optional[Decimal] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    monthly_rent: Optional[Decimal] = None
    security_deposit: Optional[Decimal] = None
    status: Optional[str] = Field(None, pattern="^(vacant|occupied|maintenance|unavailable)$")
    available_date: Optional[date] = None
    has_washer_dryer: Optional[bool] = None
    has_dishwasher: Optional[bool] = None
    has_ac: Optional[bool] = None
    has_balcony: Optional[bool] = None
    smart_lock_entity_id: Optional[str] = Field(None, max_length=255)
    thermostat_entity_id: Optional[str] = Field(None, max_length=255)
    energy_sensor_entity_id: Optional[str] = Field(None, max_length=255)
    water_sensor_entity_id: Optional[str] = Field(None, max_length=255)
    occupancy_sensor_entity_id: Optional[str] = Field(None, max_length=255)


class Unit(UnitBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TENANT SCHEMAS
# ============================================================================

class TenantBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    employer: Optional[str] = Field(None, max_length=255)
    employment_status: Optional[str] = Field(None, max_length=50)
    annual_income: Optional[Decimal] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, max_length=50)
    move_in_preference: Optional[date] = None
    notes: Optional[str] = None
    portal_enabled: bool = False
    status: str = Field(default="applicant", pattern="^(applicant|active|former)$")


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    employer: Optional[str] = Field(None, max_length=255)
    employment_status: Optional[str] = Field(None, max_length=50)
    annual_income: Optional[Decimal] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, max_length=50)
    move_in_preference: Optional[date] = None
    notes: Optional[str] = None
    portal_enabled: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(applicant|active|former)$")


class Tenant(TenantBase):
    id: UUID
    auth_user_id: Optional[str] = None
    email: str  # Override EmailStr to allow .local domains when reading from DB
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# LEASE SCHEMAS
# ============================================================================

class LeaseBase(BaseModel):
    unit_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    rent_amount: Decimal
    security_deposit: Optional[Decimal] = None
    rent_due_day: int = Field(default=1, ge=1, le=31)
    late_fee_amount: Decimal = Field(default=0)
    late_fee_grace_days: int = Field(default=3, ge=0)
    pet_deposit: Decimal = Field(default=0)
    parking_fee: Decimal = Field(default=0)
    status: str = Field(default="active", pattern="^(active|expired|terminated|pending)$")
    notes: Optional[str] = None
    lease_document_id: Optional[UUID] = None


class LeaseCreate(LeaseBase):
    pass


class LeaseUpdate(BaseModel):
    end_date: Optional[date] = None
    rent_amount: Optional[Decimal] = None
    security_deposit: Optional[Decimal] = None
    rent_due_day: Optional[int] = Field(None, ge=1, le=31)
    late_fee_amount: Optional[Decimal] = None
    late_fee_grace_days: Optional[int] = Field(None, ge=0)
    pet_deposit: Optional[Decimal] = None
    parking_fee: Optional[Decimal] = None
    status: Optional[str] = Field(None, pattern="^(active|expired|terminated|pending)$")
    notes: Optional[str] = None
    lease_document_id: Optional[UUID] = None


class Lease(LeaseBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# LIST RESPONSE SCHEMAS
# ============================================================================

class PropertyList(BaseModel):
    total: int
    items: List[Property]


class BuildingList(BaseModel):
    total: int
    items: List[Building]


class UnitList(BaseModel):
    total: int
    items: List[Unit]


class TenantList(BaseModel):
    total: int
    items: List[Tenant]


class LeaseList(BaseModel):
    total: int
    items: List[Lease]


# ============================================================================
# PAGINATED RESPONSE SCHEMAS
# ============================================================================

class TenantResponse(Tenant):
    """Single tenant response"""
    pass


class TenantListResponse(BaseModel):
    """Paginated tenant list response"""
    items: List[Tenant]
    total: int
    skip: int
    limit: int


class LeaseResponse(Lease):
    """Single lease response"""
    pass


class LeaseListResponse(BaseModel):
    """Paginated lease list response"""
    items: List[Lease]
    total: int
    skip: int
    limit: int


# ============================================================================
# PAYMENT SCHEMAS
# ============================================================================

class RentPaymentCreate(BaseModel):
    """
    Schema for creating a rent payment

    EPIC D: Payment Linkage Invariants
    - tenant_id and unit_id are required and must match the lease's tenant_id and unit_id
    - API validates consistency before database insertion
    - Database trigger provides additional validation layer
    """
    lease_id: UUID
    tenant_id: UUID
    unit_id: UUID
    amount: Decimal
    due_date: date
    payment_method: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RentPaymentUpdate(BaseModel):
    """Schema for updating a rent payment"""
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None
    late_fee_charged: Optional[Decimal] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RentPaymentResponse(BaseModel):
    """Single rent payment response"""
    id: UUID
    lease_id: UUID
    tenant_id: UUID
    unit_id: UUID
    amount: Decimal
    due_date: date
    paid_date: Optional[date] = None
    payment_method: Optional[str] = None
    status: str
    late_fee_charged: Optional[Decimal] = None
    notes: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    stripe_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentPaymentListResponse(BaseModel):
    """Paginated rent payment list response"""
    items: List[RentPaymentResponse]
    total: int
    skip: int
    limit: int


class StripePaymentIntentCreate(BaseModel):
    """Schema for creating a Stripe payment intent"""
    payment_id: UUID
    return_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StripePaymentIntentResponse(BaseModel):
    """Response with Stripe payment intent details"""
    client_secret: str
    payment_intent_id: str
    amount: Decimal
    currency: str
    status: str
    publishable_key: str

    model_config = ConfigDict(from_attributes=True)


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event payload"""
    type: str
    data: Dict[str, Any]


class StripeRefundRequest(BaseModel):
    """Schema for requesting a refund"""
    amount: Optional[Decimal] = None
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORK ORDER SCHEMAS
# ============================================================================

class WorkOrderCreate(BaseModel):
    """Schema for creating a work order"""
    unit_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    title: str
    description: str
    category: str
    priority: str = "normal"
    estimated_cost: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderUpdate(BaseModel):
    """Schema for updating a work order"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    tenant_accessible: Optional[bool] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderAssign(BaseModel):
    """Schema for assigning a work order"""
    assigned_to: UUID

    model_config = ConfigDict(from_attributes=True)


class WorkOrderComplete(BaseModel):
    """Schema for completing a work order"""
    actual_cost: Optional[Decimal] = None
    completion_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderResponse(BaseModel):
    """Single work order response"""
    id: UUID
    unit_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    title: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[UUID] = None
    reported_date: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    tenant_accessible: bool = True
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: Optional[List['WorkOrderTaskResponse']] = []
    materials: Optional[List['WorkOrderMaterialResponse']] = []
    events: Optional[List['WorkOrderEventResponse']] = []

    model_config = ConfigDict(from_attributes=True)


class WorkOrderListResponse(BaseModel):
    """Paginated work order list response"""
    items: List[WorkOrderResponse]
    total: int
    skip: int
    limit: int


class WorkOrderEventCreate(BaseModel):
    """Schema for creating a work order event"""
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_by: Optional[str] = None
    created_by_type: str = "staff"
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderEventResponse(BaseModel):
    """Work order event response"""
    id: UUID
    work_order_id: UUID
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_by: Optional[str] = None
    created_by_type: str
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORK ORDER TASK SCHEMAS
# ============================================================================

class WorkOrderTaskCreate(BaseModel):
    """Schema for creating a work order task"""
    title: str
    notes: Optional[str] = None
    estimate_hours: Optional[Decimal] = None
    sequence: int = 0
    status: str = "pending"

    model_config = ConfigDict(from_attributes=True)


class WorkOrderTaskUpdate(BaseModel):
    """Schema for updating a work order task"""
    title: Optional[str] = None
    notes: Optional[str] = None
    estimate_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    sequence: Optional[int] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderTaskResponse(BaseModel):
    """Work order task response"""
    id: UUID
    work_order_id: UUID
    title: str
    notes: Optional[str] = None
    estimate_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    sequence: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# WORK ORDER MATERIAL SCHEMAS
# ============================================================================

class WorkOrderMaterialCreate(BaseModel):
    """Schema for creating a work order material"""
    item: str
    qty: Decimal
    unit_cost: Decimal
    extended_cost: Optional[Decimal] = None  # Auto-calculated if not provided
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('extended_cost', mode='before')
    @classmethod
    def calculate_extended_cost(cls, v, info):
        """Calculate extended cost if not provided"""
        if v is None and 'qty' in info.data and 'unit_cost' in info.data:
            return info.data['qty'] * info.data['unit_cost']
        return v


class WorkOrderMaterialUpdate(BaseModel):
    """Schema for updating a work order material"""
    item: Optional[str] = None
    qty: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderMaterialResponse(BaseModel):
    """Work order material response"""
    id: UUID
    work_order_id: UUID
    item: str
    qty: Decimal
    unit_cost: Decimal
    extended_cost: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SMART HOME SERVICE SCHEMAS
# ============================================================================

# ----------------------------------------------------------------------------
# SERVICE PACKAGE SCHEMAS (Tiered Offerings: Basic/Premium/Enterprise)
# ----------------------------------------------------------------------------

class ServicePackageBase(BaseModel):
    """Base schema for service package (tiered smart home offerings)"""
    name: str = Field(..., max_length=100, description="Package name (e.g., 'Basic Smart Home')")
    description: Optional[str] = Field(None, description="Detailed package description")
    monthly_fee: Decimal = Field(..., ge=0, description="Monthly service fee")
    installation_fee: Decimal = Field(default=0, ge=0, description="One-time installation fee")
    annual_discount_percent: Decimal = Field(default=0, ge=0, le=100, description="Annual subscription discount %")
    included_services: Optional[List[str]] = Field(None, description="Services included (e.g., ['monitoring', 'automation'])")
    included_device_count: int = Field(default=0, ge=0, description="Number of devices included")
    sla_response_time_hours: int = Field(default=48, ge=1, description="Support response SLA in hours")
    features: Optional[Dict[str, Any]] = Field(None, description="Detailed feature list")
    active: bool = Field(default=True, description="Package is active and available")


class ServicePackageCreate(ServicePackageBase):
    """Schema for creating a new service package"""
    pass


class ServicePackageUpdate(BaseModel):
    """Schema for updating an existing service package"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    monthly_fee: Optional[Decimal] = Field(None, ge=0)
    installation_fee: Optional[Decimal] = Field(None, ge=0)
    annual_discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    included_services: Optional[List[str]] = None
    included_device_count: Optional[int] = Field(None, ge=0)
    sla_response_time_hours: Optional[int] = Field(None, ge=1)
    features: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class ServicePackage(ServicePackageBase):
    """Service package response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServicePackageListResponse(BaseModel):
    """Paginated service package list response"""
    items: List[ServicePackage]
    total: int
    skip: int
    limit: int


# ----------------------------------------------------------------------------
# SERVICE CONTRACT SCHEMAS (Smart Home Service Agreements)
# ----------------------------------------------------------------------------

class ServiceContractBase(BaseModel):
    """Base schema for service contract (smart home service agreements)"""
    client_id: UUID = Field(..., description="Client (tenant) subscribing to service")
    property_id: UUID = Field(..., description="Property where service is deployed")
    package_id: UUID = Field(..., description="Service package selected")
    contract_type: str = Field(
        default="monthly",
        pattern="^(monthly|annual|project)$",
        description="Contract type: monthly, annual, or one-time project"
    )
    start_date: date = Field(..., description="Service contract start date")
    end_date: Optional[date] = Field(None, description="Contract end date (null for ongoing monthly)")
    auto_renew: bool = Field(default=True, description="Automatically renew contract")
    monthly_fee: Decimal = Field(..., ge=0, description="Monthly service fee")
    installation_fee: Decimal = Field(default=0, ge=0, description="One-time installation fee")
    status: str = Field(
        default="draft",
        pattern="^(draft|active|paused|cancelled|completed)$",
        description="Contract status"
    )
    installation_completed: bool = Field(default=False, description="Installation has been completed")
    installation_date: Optional[date] = Field(None, description="Date installation was completed")
    notes: Optional[str] = Field(None, description="Contract notes")


class ServiceContractCreate(ServiceContractBase):
    """Schema for creating a new service contract"""
    pass


class ServiceContractUpdate(BaseModel):
    """Schema for updating an existing service contract"""
    end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    monthly_fee: Optional[Decimal] = Field(None, ge=0)
    installation_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(draft|active|paused|cancelled|completed)$")
    installation_completed: Optional[bool] = None
    installation_date: Optional[date] = None
    notes: Optional[str] = None


class ServiceContract(ServiceContractBase):
    """Service contract response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceContractListResponse(BaseModel):
    """Paginated service contract list response"""
    items: List[ServiceContract]
    total: int
    skip: int
    limit: int


# ----------------------------------------------------------------------------
# INSTALLATION SCHEMAS (Installation Project Tracking)
# ----------------------------------------------------------------------------

class InstallationBase(BaseModel):
    """Base schema for installation project"""
    client_id: UUID = Field(..., description="Client receiving installation")
    property_id: UUID = Field(..., description="Property where installation occurs")
    contract_id: UUID = Field(..., description="Associated service contract")
    status: str = Field(
        default="scheduled",
        pattern="^(scheduled|in_progress|completed|cancelled)$",
        description="Installation status"
    )
    scheduled_date: date = Field(..., description="Scheduled installation date")
    completion_date: Optional[date] = Field(None, description="Actual completion date")
    installer_id: Optional[UUID] = Field(None, description="Staff or contractor ID")
    installer_name: Optional[str] = Field(None, max_length=255, description="Installer name")
    devices_to_install: Optional[List[Dict[str, Any]]] = Field(None, description="Planned devices")
    devices_installed: Optional[List[UUID]] = Field(None, description="IDs of installed devices")
    installation_notes: Optional[str] = Field(None, description="Installation notes")
    completion_certificate_id: Optional[UUID] = Field(None, description="Document ID of completion certificate")
    total_cost: Decimal = Field(default=0, ge=0, description="Total installation cost")
    labor_hours: Decimal = Field(default=0, ge=0, description="Labor hours worked")
    labor_cost: Decimal = Field(default=0, ge=0, description="Labor cost")
    materials_cost: Decimal = Field(default=0, ge=0, description="Materials cost")


class InstallationCreate(InstallationBase):
    """Schema for creating a new installation project"""
    pass


class InstallationUpdate(BaseModel):
    """Schema for updating an existing installation"""
    status: Optional[str] = Field(None, pattern="^(scheduled|in_progress|completed|cancelled)$")
    scheduled_date: Optional[date] = None
    completion_date: Optional[date] = None
    installer_id: Optional[UUID] = None
    installer_name: Optional[str] = Field(None, max_length=255)
    devices_to_install: Optional[List[Dict[str, Any]]] = None
    devices_installed: Optional[List[UUID]] = None
    installation_notes: Optional[str] = None
    completion_certificate_id: Optional[UUID] = None
    total_cost: Optional[Decimal] = Field(None, ge=0)
    labor_hours: Optional[Decimal] = Field(None, ge=0)
    labor_cost: Optional[Decimal] = Field(None, ge=0)
    materials_cost: Optional[Decimal] = Field(None, ge=0)


class Installation(InstallationBase):
    """Installation response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstallationListResponse(BaseModel):
    """Paginated installation list response"""
    items: List[Installation]
    total: int
    skip: int
    limit: int


# ----------------------------------------------------------------------------
# SMART DEVICE SCHEMAS (Device Inventory Management)
# ----------------------------------------------------------------------------

class SmartDeviceBase(BaseModel):
    """Base schema for smart device inventory"""
    property_id: UUID = Field(..., description="Property where device is installed")
    client_id: Optional[UUID] = Field(None, description="Client who owns/uses device")
    service_contract_id: Optional[UUID] = Field(None, description="Associated service contract")
    device_type: str = Field(..., max_length=50, description="Device type (sensor, switch, camera, etc.)")
    manufacturer: Optional[str] = Field(None, max_length=100, description="Device manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Device model")
    serial_number: Optional[str] = Field(None, max_length=100, description="Device serial number")
    installation_date: Optional[date] = Field(None, description="Date device was installed")
    warranty_expiration: Optional[date] = Field(None, description="Warranty expiration date")
    firmware_version: Optional[str] = Field(None, max_length=50, description="Current firmware version")
    mqtt_topic: Optional[str] = Field(None, max_length=255, description="MQTT topic for device")
    ha_entity_id: Optional[str] = Field(None, max_length=255, description="Home Assistant entity ID")
    edge_node_id: Optional[UUID] = Field(None, description="Edge node managing this device")
    status: str = Field(
        default="active",
        pattern="^(active|inactive|maintenance|failed|retired)$",
        description="Device operational status"
    )
    health_status: str = Field(
        default="healthy",
        pattern="^(healthy|warning|critical|unknown)$",
        description="Device health status"
    )
    last_seen: Optional[datetime] = Field(None, description="Last communication from device")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    replacement_due: Optional[date] = Field(None, description="Recommended replacement date")
    notes: Optional[str] = Field(None, description="Device notes")


class SmartDeviceCreate(SmartDeviceBase):
    """Schema for creating a new smart device"""
    pass


class SmartDeviceUpdate(BaseModel):
    """Schema for updating an existing smart device"""
    client_id: Optional[UUID] = None
    service_contract_id: Optional[UUID] = None
    device_type: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    installation_date: Optional[date] = None
    warranty_expiration: Optional[date] = None
    firmware_version: Optional[str] = Field(None, max_length=50)
    mqtt_topic: Optional[str] = Field(None, max_length=255)
    ha_entity_id: Optional[str] = Field(None, max_length=255)
    edge_node_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|maintenance|failed|retired)$")
    health_status: Optional[str] = Field(None, pattern="^(healthy|warning|critical|unknown)$")
    last_seen: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    replacement_due: Optional[date] = None
    notes: Optional[str] = None


class SmartDevice(SmartDeviceBase):
    """Smart device response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SmartDeviceListResponse(BaseModel):
    """Paginated smart device list response"""
    items: List[SmartDevice]
    total: int
    skip: int
    limit: int


# ----------------------------------------------------------------------------
# PROPERTY EDGE NODE SCHEMAS (Home Assistant Instances)
# ----------------------------------------------------------------------------

class PropertyEdgeNodeBase(BaseModel):
    """Base schema for property edge node (Home Assistant instance)"""
    property_id: UUID = Field(..., description="Property managed by this edge node (one-to-one)")

    # Parent Hub Linkage (for multi-unit buildings)
    parent_hub_id: Optional[UUID] = Field(None, description="Parent property hub ID (for residential hubs in multi-unit buildings)")

    # 4-Tier Architecture Fields
    hub_type: str = Field(default="tier_3_residential", description="Hub tier type")
    sync_status: str = Field(default="never_synced", description="Sync status with Tier 1")
    sync_error_message: Optional[str] = Field(None, description="Last sync error message")
    deployed_stack: Optional[str] = Field(None, description="Deployed stack name")
    manifest_version: Optional[str] = Field(None, description="Deployment manifest version")
    managed_by_tier1: bool = Field(default=True, description="Managed by Tier 1 hub")
    auto_update_enabled: bool = Field(default=True, description="Auto-update enabled")
    api_token_hash: Optional[str] = Field(None, description="API token hash")

    # Deployment Status
    deployment_status: str = Field(default="pending", description="Deployment status")
    deployment_started_at: Optional[datetime] = Field(None, description="Deployment start time")
    deployment_completed_at: Optional[datetime] = Field(None, description="Deployment completion time")
    deployment_error_message: Optional[str] = Field(None, description="Deployment error message")
    deployment_progress_percent: int = Field(default=0, ge=0, le=100, description="Deployment progress")
    deployment_current_step: Optional[str] = Field(None, description="Current deployment step")

    # Node Configuration
    node_type: str = Field(
        default="home_assistant",
        pattern="^(home_assistant|mqtt|custom)$",
        description="Edge node type"
    )
    hostname: str = Field(..., max_length=255, description="Node hostname")
    ip_address: Optional[str] = Field(None, description="Node IP address")
    tailscale_ip: Optional[str] = Field(None, description="Tailscale mesh IP address")
    tailscale_hostname: Optional[str] = Field(None, max_length=255, description="Tailscale mesh hostname")
    api_token: Optional[str] = Field(None, max_length=500, description="Encrypted API token")
    api_url: Optional[str] = Field(None, max_length=500, description="API endpoint URL")
    mqtt_broker_host: Optional[str] = Field(None, max_length=255, description="MQTT broker hostname")
    mqtt_broker_port: int = Field(default=1883, ge=1, le=65535, description="MQTT broker port")
    mqtt_topics: Optional[List[str]] = Field(None, description="Subscribed MQTT topics")
    status: str = Field(
        default="offline",
        pattern="^(online|offline|error|maintenance)$",
        description="Node connection status"
    )
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    last_sync: Optional[datetime] = Field(None, description="Last data sync timestamp")
    firmware_version: Optional[str] = Field(None, max_length=50, description="Node firmware/HA version")
    device_count: int = Field(default=0, ge=0, description="Number of managed devices")
    automation_count: int = Field(default=0, ge=0, description="Number of automations")
    uptime_hours: int = Field(default=0, ge=0, description="Node uptime in hours")
    resource_usage: Optional[Dict[str, Any]] = Field(None, description="Resource usage metrics (CPU, memory, disk)")

    @field_validator('ip_address', 'tailscale_ip', mode='before')
    @classmethod
    def convert_ip_to_string(cls, value):
        """Convert IPv4Address/IPv6Address objects to strings before validation"""
        if value is None:
            return None
        # If it's already a string, return as-is
        if isinstance(value, str):
            return value
        # Convert IPv4Address/IPv6Address objects to strings
        return str(value)


class PropertyEdgeNodeCreate(PropertyEdgeNodeBase):
    """Schema for creating a new property edge node"""
    pass


class PropertyEdgeNodeUpdate(BaseModel):
    """Schema for updating an existing property edge node"""
    # Parent Hub Linkage
    parent_hub_id: Optional[UUID] = None

    # 4-Tier Architecture Fields
    hub_type: Optional[str] = None
    sync_status: Optional[str] = None
    sync_error_message: Optional[str] = None
    deployed_stack: Optional[str] = None
    manifest_version: Optional[str] = None
    managed_by_tier1: Optional[bool] = None
    auto_update_enabled: Optional[bool] = None
    api_token_hash: Optional[str] = None

    # Deployment Status
    deployment_status: Optional[str] = None
    deployment_started_at: Optional[datetime] = None
    deployment_completed_at: Optional[datetime] = None
    deployment_error_message: Optional[str] = None
    deployment_progress_percent: Optional[int] = Field(None, ge=0, le=100)
    deployment_current_step: Optional[str] = None

    # Node Configuration
    node_type: Optional[str] = Field(None, pattern="^(home_assistant|mqtt|custom)$")
    hostname: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = None
    tailscale_ip: Optional[str] = None
    tailscale_hostname: Optional[str] = Field(None, max_length=255)
    api_token: Optional[str] = Field(None, max_length=500)
    api_url: Optional[str] = Field(None, max_length=500)
    mqtt_broker_host: Optional[str] = Field(None, max_length=255)
    mqtt_broker_port: Optional[int] = Field(None, ge=1, le=65535)
    mqtt_topics: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(online|offline|error|maintenance)$")
    last_heartbeat: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    firmware_version: Optional[str] = Field(None, max_length=50)
    device_count: Optional[int] = Field(None, ge=0)
    automation_count: Optional[int] = Field(None, ge=0)
    uptime_hours: Optional[int] = Field(None, ge=0)
    resource_usage: Optional[Dict[str, Any]] = None


class PropertyEdgeNode(PropertyEdgeNodeBase):
    """Property edge node response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropertyEdgeNodeListResponse(BaseModel):
    """Paginated property edge node list response"""
    items: List[PropertyEdgeNode]
    total: int
    skip: int
    limit: int


# ----------------------------------------------------------------------------
# EXTENDED TENANT SCHEMAS (with Smart Home Service fields)
# ----------------------------------------------------------------------------

class TenantServiceUpdate(BaseModel):
    """Schema for updating tenant's smart home service subscription"""
    client_type: Optional[str] = Field(
        None,
        pattern="^(rental_tenant|service_subscriber|both)$",
        description="Client type: rental_tenant, service_subscriber, or both"
    )
    service_tier: Optional[str] = Field(None, max_length=50, description="Service tier (basic, premium, enterprise)")
    subscription_status: Optional[str] = Field(
        None,
        pattern="^(inactive|active|paused|cancelled)$",
        description="Subscription status"
    )
    service_contract_start: Optional[date] = Field(None, description="Service contract start date")
    service_contract_end: Optional[date] = Field(None, description="Service contract end date")
    billing_cycle: Optional[str] = Field(
        None,
        pattern="^(monthly|annual|one-time)$",
        description="Billing cycle"
    )


# Extend existing Tenant response to include service fields
class TenantWithServices(Tenant):
    """Tenant response including smart home service subscription details"""
    client_type: str
    service_tier: Optional[str] = None
    subscription_status: str
    service_contract_start: Optional[date] = None
    service_contract_end: Optional[date] = None
    billing_cycle: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CLIENT MANAGEMENT SCHEMAS (Somni Intelligent Living as a Service)
# ============================================================================

class ClientBase(BaseModel):
    """Base schema for Client (Somni ILaaS customer) with comprehensive onboarding"""
    name: str = Field(..., max_length=255, description="Client name")
    tier: str = Field(..., pattern="^(tier_0|tier_1|tier_2)$", description="Service tier: tier_0 (self-managed), tier_1 (managed), tier_2 (enterprise)")
    client_type: str = Field(default="multi-unit", pattern="^(multi-unit|single-family)$", description="Client type: multi-unit (property manager) or single-family (homeowner)")

    # Contact Information (Original)
    email: EmailStr = Field(..., description="Client email")
    phone: Optional[str] = Field(None, max_length=20, description="Client phone")
    address_line1: Optional[str] = Field(None, max_length=255, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=50, description="State")
    zip_code: Optional[str] = Field(None, max_length=20, description="Zip code")
    country: str = Field(default="USA", max_length=100, description="Country")

    # Primary Contact Information
    primary_contact_name: Optional[str] = Field(None, max_length=255, description="Primary contact person name")
    primary_contact_title: Optional[str] = Field(None, max_length=100, description="Primary contact job title")
    primary_contact_phone: Optional[str] = Field(None, max_length=20, description="Primary contact phone")
    primary_contact_email: Optional[EmailStr] = Field(None, description="Primary contact email")

    # Secondary Contact Information
    secondary_contact_name: Optional[str] = Field(None, max_length=255, description="Secondary contact person name")
    secondary_contact_title: Optional[str] = Field(None, max_length=100, description="Secondary contact job title")
    secondary_contact_phone: Optional[str] = Field(None, max_length=20, description="Secondary contact phone")
    secondary_contact_email: Optional[EmailStr] = Field(None, description="Secondary contact email")

    # Property Information
    property_name: Optional[str] = Field(None, max_length=255, description="Property name")
    property_address_line1: Optional[str] = Field(None, max_length=255, description="Property address line 1")
    property_address_line2: Optional[str] = Field(None, max_length=255, description="Property address line 2")
    property_city: Optional[str] = Field(None, max_length=100, description="Property city")
    property_state: Optional[str] = Field(None, max_length=50, description="Property state")
    property_zip_code: Optional[str] = Field(None, max_length=20, description="Property zip code")
    property_country: str = Field(default="USA", max_length=100, description="Property country")

    # Property Details
    property_type: Optional[str] = Field(None, pattern="^(single_family|multi_unit|commercial|mixed_use|other)$", description="Property type")
    property_unit_count: Optional[int] = Field(None, ge=0, description="Number of units")
    property_year_built: Optional[int] = Field(None, ge=1800, le=2100, description="Year property was built")
    property_square_feet: Optional[int] = Field(None, ge=0, description="Total square footage")
    property_description: Optional[str] = Field(None, description="Property description")

    # Onboarding Workflow
    onboarding_stage: str = Field(default="initial", pattern="^(initial|discovery|assessment|proposal|contract|deployment|completed)$", description="Current onboarding stage")
    onboarding_step: int = Field(default=1, ge=1, description="Current step within stage")
    onboarding_progress_percent: int = Field(default=0, ge=0, le=100, description="Overall onboarding progress percentage")
    discovery_call_scheduled_at: Optional[datetime] = Field(None, description="When discovery call is scheduled")
    discovery_call_completed_at: Optional[datetime] = Field(None, description="When discovery call was completed")
    initial_assessment_completed: bool = Field(default=False, description="Has initial assessment been completed")

    # Initial Transcript/Notes
    discovery_call_transcript: Optional[str] = Field(None, description="Full transcript of discovery call")
    initial_notes: Optional[str] = Field(None, description="Initial notes from first contact")
    special_requirements: Optional[str] = Field(None, description="Special requirements or considerations")

    # Communication Preferences
    preferred_contact_method: str = Field(default="email", pattern="^(email|phone|sms|any)$", description="Preferred contact method")
    preferred_contact_time: Optional[str] = Field(None, max_length=50, description="Preferred time to be contacted")
    timezone: str = Field(default="America/New_York", max_length=50, description="Client timezone")

    # Billing Information
    subscription_plan: Optional[str] = Field(None, max_length=100, description="Subscription plan name")
    monthly_fee: Optional[Decimal] = Field(None, ge=0, description="Monthly subscription fee")
    billing_status: str = Field(default="active", pattern="^(active|suspended|cancelled|past_due)$", description="Billing status")

    # SLA Information
    support_level: Optional[str] = Field(None, max_length=50, description="Support level: self-managed, managed, enterprise")
    response_time_hours: Optional[int] = Field(None, ge=1, description="SLA response time in hours")
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100, description="Uptime guarantee percentage (e.g., 99.00 for 99%)")

    # Tier 2 Enterprise Specific
    is_landlord_client: bool = Field(default=False, description="Is this a property manager/landlord client")
    rent_collection_fee_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="Rent collection fee percentage (Tier 2 Type A)")

    # Infrastructure Links
    edge_node_id: Optional[UUID] = Field(None, description="Linked PropertyEdgeNode (Tier 1/2)")
    property_id: Optional[UUID] = Field(None, description="Linked Property (Tier 2 Type A)")

    # Account Status
    status: str = Field(default="active", pattern="^(active|suspended|cancelled|churned)$", description="Client account status")
    onboarding_completed: bool = Field(default=False, description="Has onboarding been completed")
    onboarded_at: Optional[datetime] = Field(None, description="Onboarding completion timestamp")
    churned_at: Optional[datetime] = Field(None, description="Churn timestamp")
    churn_reason: Optional[str] = Field(None, description="Reason for churn")

    # Notes
    notes: Optional[str] = Field(None, description="Client notes")


class ClientCreate(ClientBase):
    """Schema for creating a new client"""
    pass


class ClientUpdate(BaseModel):
    """Schema for updating an existing client"""
    name: Optional[str] = Field(None, max_length=255)
    tier: Optional[str] = Field(None, pattern="^(tier_0|tier_1|tier_2)$")
    client_type: Optional[str] = Field(None, pattern="^(multi-unit|single-family)$")

    # Contact Information (Original)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    # Primary Contact Information
    primary_contact_name: Optional[str] = Field(None, max_length=255)
    primary_contact_title: Optional[str] = Field(None, max_length=100)
    primary_contact_phone: Optional[str] = Field(None, max_length=20)
    primary_contact_email: Optional[EmailStr] = None

    # Secondary Contact Information
    secondary_contact_name: Optional[str] = Field(None, max_length=255)
    secondary_contact_title: Optional[str] = Field(None, max_length=100)
    secondary_contact_phone: Optional[str] = Field(None, max_length=20)
    secondary_contact_email: Optional[EmailStr] = None

    # Property Information
    property_name: Optional[str] = Field(None, max_length=255)
    property_address_line1: Optional[str] = Field(None, max_length=255)
    property_address_line2: Optional[str] = Field(None, max_length=255)
    property_city: Optional[str] = Field(None, max_length=100)
    property_state: Optional[str] = Field(None, max_length=50)
    property_zip_code: Optional[str] = Field(None, max_length=20)
    property_country: Optional[str] = Field(None, max_length=100)

    # Property Details
    property_type: Optional[str] = Field(None, pattern="^(single_family|multi_unit|commercial|mixed_use|other)$")
    property_unit_count: Optional[int] = Field(None, ge=0)
    property_year_built: Optional[int] = Field(None, ge=1800, le=2100)
    property_square_feet: Optional[int] = Field(None, ge=0)
    property_description: Optional[str] = None

    # Onboarding Workflow
    onboarding_stage: Optional[str] = Field(None, pattern="^(initial|discovery|assessment|proposal|contract|deployment|completed)$")
    onboarding_step: Optional[int] = Field(None, ge=1)
    onboarding_progress_percent: Optional[int] = Field(None, ge=0, le=100)
    discovery_call_scheduled_at: Optional[datetime] = None
    discovery_call_completed_at: Optional[datetime] = None
    initial_assessment_completed: Optional[bool] = None

    # Initial Transcript/Notes
    discovery_call_transcript: Optional[str] = None
    initial_notes: Optional[str] = None
    special_requirements: Optional[str] = None

    # Communication Preferences
    preferred_contact_method: Optional[str] = Field(None, pattern="^(email|phone|sms|any)$")
    preferred_contact_time: Optional[str] = Field(None, max_length=50)
    timezone: Optional[str] = Field(None, max_length=50)

    # Billing Information
    subscription_plan: Optional[str] = Field(None, max_length=100)
    monthly_fee: Optional[Decimal] = Field(None, ge=0)
    billing_status: Optional[str] = Field(None, pattern="^(active|suspended|cancelled|past_due)$")

    # SLA Information
    support_level: Optional[str] = Field(None, max_length=50)
    response_time_hours: Optional[int] = Field(None, ge=1)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)

    # Tier 2 Enterprise Specific
    is_landlord_client: Optional[bool] = None
    rent_collection_fee_percent: Optional[Decimal] = Field(None, ge=0, le=100)

    # Infrastructure Links
    edge_node_id: Optional[UUID] = None
    property_id: Optional[UUID] = None

    # Account Status
    status: Optional[str] = Field(None, pattern="^(active|suspended|cancelled|churned)$")
    onboarding_completed: Optional[bool] = None
    onboarded_at: Optional[datetime] = None
    churned_at: Optional[datetime] = None
    churn_reason: Optional[str] = None

    # Notes
    notes: Optional[str] = None


class Client(ClientBase):
    """Client response with metadata"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientListResponse(BaseModel):
    """Paginated client list response"""
    items: List[Client]
    total: int
    skip: int
    limit: int


class ClientInfrastructureResponse(BaseModel):
    """Response with client's linked infrastructure details"""
    client_id: UUID
    client_name: str
    client_tier: str

    # PropertyEdgeNode details (if linked)
    edge_node: Optional[PropertyEdgeNode] = None

    # Property details (if linked)
    property: Optional[Property] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CLIENT MEDIA SCHEMAS (Client Portfolio Management)
# ============================================================================

class ClientMediaBase(BaseModel):
    """Base schema for client media files"""
    # Media Classification
    media_type: str = Field(..., pattern="^(photo|video|floorplan|3d_model|document|other)$", description="Type of media")
    media_category: str = Field(..., pattern="^(property_exterior|property_interior|unit_example|amenities|floorplan|site_plan|3d_model|permit|inspection|other)$", description="Category of media")

    # Metadata
    title: Optional[str] = Field(None, max_length=255, description="Media title")
    description: Optional[str] = Field(None, description="Media description")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization and search")
    captured_date: Optional[date] = Field(None, description="Date when media was captured")

    # Visibility
    is_public: bool = Field(default=False, description="Is this media publicly visible")
    is_featured: bool = Field(default=False, description="Is this a featured item")
    display_order: int = Field(default=0, ge=0, description="Display order (lower numbers appear first)")


class ClientMediaCreate(ClientMediaBase):
    """Schema for creating client media (used after file upload)"""
    client_id: UUID = Field(..., description="Client this media belongs to")

    # File Information (set by upload handler)
    file_name: str = Field(..., max_length=500, description="Generated unique filename")
    original_file_name: str = Field(..., max_length=500, description="Original filename from upload")
    file_extension: str = Field(..., max_length=10, description="File extension")
    mime_type: str = Field(..., max_length=100, description="MIME type")
    file_size_bytes: int = Field(..., gt=0, description="File size in bytes")

    # Storage (set by upload handler)
    minio_bucket: str = Field(..., max_length=100, description="MinIO bucket name")
    minio_object_key: str = Field(..., max_length=500, description="MinIO object key")
    minio_url: Optional[str] = Field(None, description="MinIO presigned URL")

    # Optional metadata (extracted during processing)
    width: Optional[int] = Field(None, ge=0, description="Image/video width in pixels")
    height: Optional[int] = Field(None, ge=0, description="Image/video height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")
    page_count: Optional[int] = Field(None, ge=1, description="Number of pages (for documents)")
    model_format: Optional[str] = Field(None, max_length=10, description="3D model format (GLB, USDZ, etc.)")
    polygon_count: Optional[int] = Field(None, ge=0, description="3D model polygon count")
    model_dimensions: Optional[Dict[str, Any]] = Field(None, description="3D model dimensions")

    # Upload tracking
    uploaded_by: Optional[str] = Field(None, max_length=255, description="Who uploaded this media")
    upload_source: str = Field(default="web_ui", pattern="^(web_ui|mobile_app|api|email|bulk_import)$", description="Upload source")


class ClientMediaUpdate(BaseModel):
    """Schema for updating client media metadata"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    captured_date: Optional[date] = None
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)
    media_category: Optional[str] = Field(None, pattern="^(property_exterior|property_interior|unit_example|amenities|floorplan|site_plan|3d_model|permit|inspection|other)$")


class ClientMedia(ClientMediaBase):
    """Client media response with all fields"""
    id: UUID
    client_id: UUID

    # File Information
    file_name: str
    original_file_name: str
    file_extension: str
    mime_type: str
    file_size_bytes: int

    # Storage
    minio_bucket: str
    minio_object_key: str
    minio_url: Optional[str]
    cdn_url: Optional[str]

    # Thumbnails
    thumbnail_minio_key: Optional[str]
    thumbnail_url: Optional[str]

    # Media-specific metadata
    width: Optional[int]
    height: Optional[int]
    duration_seconds: Optional[int]
    frame_rate: Optional[Decimal]
    page_count: Optional[int]
    document_version: Optional[str]
    model_format: Optional[str]
    polygon_count: Optional[int]
    model_dimensions: Optional[Dict[str, Any]]

    # Processing
    processing_status: str
    processing_error: Optional[str]
    thumbnail_generated: bool

    # Upload tracking
    uploaded_by: Optional[str]
    upload_source: str
    upload_ip_address: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ClientMediaListResponse(BaseModel):
    """Paginated client media list response"""
    items: List[ClientMedia]
    total: int
    skip: int
    limit: int


class ClientMediaUploadResponse(BaseModel):
    """Response after file upload"""
    media_id: UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    minio_url: str
    processing_status: str
    message: str = "File uploaded successfully"


class ClientMediaBulkDeleteRequest(BaseModel):
    """Request to delete multiple media files"""
    media_ids: List[UUID] = Field(..., min_length=1, max_length=100, description="List of media IDs to delete")


class ClientMediaBulkDeleteResponse(BaseModel):
    """Response after bulk delete"""
    deleted_count: int
    failed_ids: List[UUID] = Field(default_factory=list)
    errors: Dict[str, str] = Field(default_factory=dict)


class ClientMediaStatistics(BaseModel):
    """Statistics for client media"""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    photos_count: int
    videos_count: int
    floorplans_count: int
    models_3d_count: int
    documents_count: int


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    """Base alert schema"""
    hub_id: Optional[UUID] = None
    severity: str = Field(..., pattern="^(info|warning|critical)$")
    source: str = Field(..., max_length=50)
    category: str = Field(..., max_length=50)
    message: str
    entity_id: Optional[str] = Field(None, max_length=255)
    alert_metadata: Optional[Dict[str, Any]] = None


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    occurred_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[str] = Field(None, pattern="^(open|acknowledged|resolved)$")
    acknowledged_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Alert(AlertBase):
    """Alert response with metadata"""
    id: UUID
    occurred_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra='ignore')


class AlertListResponse(BaseModel):
    """Paginated alert list response"""
    items: List[Alert]
    total: int
    skip: int
    limit: int


# Rebuild models that use forward references
# This must be done after all models are defined
WorkOrderResponse.model_rebuild()
