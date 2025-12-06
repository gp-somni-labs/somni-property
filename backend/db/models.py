"""
Somni Property Manager - Database Models
SQLAlchemy ORM models matching the PostgreSQL schema
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, Date, DateTime, Boolean,
    Text, ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

from db.types import GUID, INET, JSONB, ARRAY

Base = declarative_base()


# ============================================================================
# CORE TABLES: Properties, Buildings, Units
# ============================================================================

class Property(Base):
    __tablename__ = "properties"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)
    country = Column(String(100), default='USA')

    # Property details
    property_type = Column(String(50), nullable=False)
    purchase_date = Column(Date)
    purchase_price = Column(Numeric(12, 2))
    current_value = Column(Numeric(12, 2))

    # Contact info
    owner_name = Column(String(255))
    owner_email = Column(String(255))
    owner_phone = Column(String(20))

    # Integration
    ha_instance_id = Column(String(100))
    tailscale_ip = Column(INET)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    buildings = relationship("Building", back_populates="property", cascade="all, delete-orphan")
    automation_rules = relationship("AutomationRule", back_populates="property", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="property")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="property", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="property", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "property_type IN ('residential', 'commercial', 'mixed-use')",
            name='valid_property_type'
        ),
        Index('idx_properties_owner_email', 'owner_email'),
        Index('idx_properties_ha_instance', 'ha_instance_id'),
    )


class Building(Base):
    __tablename__ = "buildings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)

    # Building details
    floors = Column(Integer, nullable=False, default=1)
    total_units = Column(Integer, nullable=False, default=0)
    year_built = Column(Integer)
    square_feet = Column(Integer)

    # Utilities
    has_central_hvac = Column(Boolean, default=False)
    has_central_water = Column(Boolean, default=False)
    has_elevator = Column(Boolean, default=False)
    has_parking = Column(Boolean, default=False)
    parking_spaces = Column(Integer, default=0)

    # Integration
    mqtt_topic_prefix = Column(String(255))

    # ========================================================================
    # HUB-SPOKE FEDERATION METADATA
    # ========================================================================
    # Links this building to the Spoke that owns it and the Client who pays for it
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'))

    # Sync tracking
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    sync_status = Column(String(20), default='synced')  # synced | pending | conflict | error | stale
    sync_error_message = Column(Text)

    # Origin & Authority tracking
    created_by_hub = Column(Boolean, default=False, nullable=False)  # True = Hub created, False = Spoke created
    last_modified_by = Column(String(10), default='spoke')  # 'hub' | 'spoke'
    hub_override_at = Column(DateTime(timezone=True))
    hub_override_by = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="buildings")
    units = relationship("Unit", back_populates="building", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="building")
    iot_devices = relationship("IoTDevice", back_populates="building")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="building", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="building", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_buildings_property_id', 'property_id'),
        Index('idx_buildings_hub_id', 'hub_id'),
        Index('idx_buildings_client_id', 'client_id'),
        Index('idx_buildings_sync_status', 'sync_status'),
        Index('idx_buildings_synced_at', 'synced_at'),
        CheckConstraint(
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')",
            name='valid_building_sync_status'
        ),
        CheckConstraint(
            "last_modified_by IN ('hub', 'spoke')",
            name='valid_building_last_modified_by'
        ),
    )


class Unit(Base):
    __tablename__ = "units"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False)

    # Unit identification
    unit_number = Column(String(50), nullable=False)
    floor = Column(Integer, nullable=False, default=1)
    unit_type = Column(String(50), nullable=False)

    # Unit details
    bedrooms = Column(Numeric(3, 1), default=0)
    bathrooms = Column(Numeric(3, 1), default=1)
    square_feet = Column(Integer)
    amenities = Column(ARRAY(String))
    description = Column(Text)

    # Rental info
    monthly_rent = Column(Numeric(10, 2))
    security_deposit = Column(Numeric(10, 2))

    # Status
    status = Column(String(20), default='vacant')
    available_date = Column(Date)

    # Features
    has_washer_dryer = Column(Boolean, default=False)
    has_dishwasher = Column(Boolean, default=False)
    has_ac = Column(Boolean, default=False)
    has_balcony = Column(Boolean, default=False)

    # IoT Integration
    mqtt_topic_prefix = Column(String(255))
    smart_lock_entity_id = Column(String(255))
    thermostat_entity_id = Column(String(255))
    energy_sensor_entity_id = Column(String(255))
    water_sensor_entity_id = Column(String(255))
    occupancy_sensor_entity_id = Column(String(255))

    # ========================================================================
    # HUB-SPOKE FEDERATION METADATA
    # ========================================================================
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    sync_status = Column(String(20), default='synced')
    sync_error_message = Column(Text)
    created_by_hub = Column(Boolean, default=False, nullable=False)
    last_modified_by = Column(String(10), default='spoke')
    hub_override_at = Column(DateTime(timezone=True))
    hub_override_by = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building", back_populates="units")
    leases = relationship("Lease", back_populates="unit", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="unit")
    iot_devices = relationship("IoTDevice", back_populates="unit")
    utility_bills = relationship("UtilityBill", back_populates="unit", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="unit", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="unit")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="unit", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="unit", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('vacant', 'occupied', 'maintenance', 'unavailable')",
            name='valid_unit_status'
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')",
            name='valid_unit_sync_status'
        ),
        CheckConstraint(
            "last_modified_by IN ('hub', 'spoke')",
            name='valid_unit_last_modified_by'
        ),
        UniqueConstraint('building_id', 'unit_number', name='uq_building_unit_number'),
        Index('idx_units_building_id', 'building_id'),
        Index('idx_units_status', 'status'),
        Index('idx_units_available_date', 'available_date'),
        Index('idx_units_hub_id', 'hub_id'),
        Index('idx_units_client_id', 'client_id'),
        Index('idx_units_sync_status', 'sync_status'),
        Index('idx_units_synced_at', 'synced_at'),
    )


# ============================================================================
# PEOPLE: Tenants
# ============================================================================

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Personal info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20))
    date_of_birth = Column(Date)

    # Employment
    employer = Column(String(255))
    employment_status = Column(String(50))
    annual_income = Column(Numeric(12, 2))

    # Emergency contact
    emergency_contact_name = Column(String(255))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relationship = Column(String(50))

    # Preferences & notes
    move_in_preference = Column(Date)
    notes = Column(Text)

    # Authentication
    auth_user_id = Column(String(255))
    portal_enabled = Column(Boolean, default=False)

    # Stripe Integration
    stripe_customer_id = Column(String(255), unique=True)

    # Invoice Ninja Integration
    invoiceninja_client_id = Column(String(255), unique=True)

    # Status
    status = Column(String(20), default='applicant')

    # ========================================================================
    # SMART HOME SERVICE EXTENSIONS
    # ========================================================================
    # Client type: rental_tenant, service_subscriber, or both
    client_type = Column(String(30), default='rental_tenant')

    # Service subscription details
    service_tier = Column(String(50))  # basic, premium, enterprise
    subscription_status = Column(String(20), default='inactive')  # inactive, active, paused, cancelled
    service_contract_start = Column(Date)
    service_contract_end = Column(Date)
    billing_cycle = Column(String(20), default='monthly')  # monthly, annual, one-time

    # ========================================================================
    # HUB-SPOKE FEDERATION METADATA
    # ========================================================================
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    sync_status = Column(String(20), default='synced')
    sync_error_message = Column(Text)
    created_by_hub = Column(Boolean, default=False, nullable=False)
    last_modified_by = Column(String(10), default='spoke')
    hub_override_at = Column(DateTime(timezone=True))
    hub_override_by = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    leases = relationship("Lease", back_populates="tenant", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
    service_contracts = relationship("ServiceContract", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('applicant', 'active', 'former')",
            name='valid_tenant_status'
        ),
        CheckConstraint(
            "client_type IN ('rental_tenant', 'service_subscriber', 'both')",
            name='valid_client_type'
        ),
        CheckConstraint(
            "subscription_status IN ('inactive', 'active', 'paused', 'cancelled')",
            name='valid_subscription_status'
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')",
            name='valid_tenant_sync_status'
        ),
        CheckConstraint(
            "last_modified_by IN ('hub', 'spoke')",
            name='valid_tenant_last_modified_by'
        ),
        Index('idx_tenants_email', 'email'),
        Index('idx_tenants_status', 'status'),
        Index('idx_tenants_auth_user_id', 'auth_user_id'),
        Index('idx_tenants_client_type', 'client_type'),
        Index('idx_tenants_subscription_status', 'subscription_status'),
        Index('idx_tenants_hub_id', 'hub_id'),
        Index('idx_tenants_client_id', 'client_id'),
        Index('idx_tenants_sync_status', 'sync_status'),
        Index('idx_tenants_synced_at', 'synced_at'),
    )


# ============================================================================
# LEASES & PAYMENTS
# ============================================================================

class Lease(Base):
    __tablename__ = "leases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'), nullable=True)  # Added per spec §4.3

    # Lease terms
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    rent_amount = Column(Numeric(10, 2), nullable=False)
    security_deposit = Column(Numeric(10, 2))

    # Payment terms
    rent_due_day = Column(Integer, default=1)
    late_fee_amount = Column(Numeric(10, 2), default=0)
    late_fee_grace_days = Column(Integer, default=3)

    # Additional fees
    pet_deposit = Column(Numeric(10, 2), default=0)
    parking_fee = Column(Numeric(10, 2), default=0)
    moving_fee = Column(Numeric(10, 2), default=0)
    safety_deposit = Column(Numeric(10, 2), default=0)

    # Status
    status = Column(String(20), default='active')

    # Notes
    notes = Column(Text)

    # Documents
    lease_document_id = Column(GUID)

    # ========================================================================
    # HUB-SPOKE FEDERATION METADATA
    # ========================================================================
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    sync_status = Column(String(20), default='synced')
    sync_error_message = Column(Text)
    created_by_hub = Column(Boolean, default=False, nullable=False)
    last_modified_by = Column(String(10), default='spoke')
    hub_override_at = Column(DateTime(timezone=True))
    hub_override_by = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="leases")
    tenant = relationship("Tenant", back_populates="leases")
    rent_payments = relationship("RentPayment", back_populates="lease", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="lease")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'terminated', 'pending')",
            name='valid_lease_status'
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')",
            name='valid_lease_sync_status'
        ),
        CheckConstraint(
            "last_modified_by IN ('hub', 'spoke')",
            name='valid_lease_last_modified_by'
        ),
        Index('idx_leases_unit_id', 'unit_id'),
        Index('idx_leases_tenant_id', 'tenant_id'),
        Index('idx_leases_building_id', 'building_id'),
        Index('idx_leases_status', 'status'),
        Index('idx_leases_dates', 'start_date', 'end_date'),
        Index('idx_leases_hub_id', 'hub_id'),
        Index('idx_leases_client_id', 'client_id'),
        Index('idx_leases_sync_status', 'sync_status'),
        Index('idx_leases_synced_at', 'synced_at'),
    )


class RentPayment(Base):
    """
    Rent Payment Model

    Stores rent payment records with linkage invariants enforced:
    - tenant_id and unit_id must match the associated lease's tenant_id and unit_id
    - Database trigger enforces consistency (see migration 012_payment_linkage_invariants)
    """
    __tablename__ = "rent_payments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    lease_id = Column(GUID, ForeignKey('leases.id', ondelete='CASCADE'), nullable=False)

    # EPIC D: Payment Linkage Invariants
    # These FKs ensure payments link properly to tenants & units via leases
    # Database trigger validates these match lease.tenant_id and lease.unit_id
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'), nullable=False)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date)
    payment_method = Column(String(50))  # 'stripe', 'check', 'cash', 'ach', 'wire'

    # Status
    status = Column(String(20), default='pending')

    # Late fees
    late_fee_charged = Column(Numeric(10, 2), default=0)

    # Reference
    transaction_id = Column(String(255))
    invoice_id = Column(Integer)

    # Stripe Integration
    stripe_payment_intent_id = Column(String(255), unique=True)
    stripe_charge_id = Column(String(255))
    stripe_customer_id = Column(String(255))
    stripe_invoice_id = Column(String(255))
    stripe_status = Column(String(50))  # succeeded, pending, failed, canceled, refunded

    # Invoice Ninja Integration
    invoiceninja_invoice_id = Column(String(255))
    invoiceninja_payment_id = Column(String(255))

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lease = relationship("Lease", back_populates="rent_payments")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    unit = relationship("Unit", foreign_keys=[unit_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'late', 'partial', 'failed', 'refunded', 'processing')",
            name='valid_payment_status'
        ),
        CheckConstraint(
            "payment_method IN ('stripe', 'check', 'cash', 'ach', 'wire', 'other')",
            name='valid_payment_method'
        ),
        Index('idx_rent_payments_lease_id', 'lease_id'),
        Index('idx_rent_payments_tenant_id', 'tenant_id'),
        Index('idx_rent_payments_unit_id', 'unit_id'),
        Index('idx_rent_payments_due_date', 'due_date'),
        Index('idx_rent_payments_status', 'status'),
        Index('idx_rent_payments_stripe_payment_intent', 'stripe_payment_intent_id'),
    )


# ============================================================================
# MAINTENANCE & WORK ORDERS
# ============================================================================

class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'))
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))

    # Work order details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), default='normal')

    # Status tracking
    status = Column(String(20), default='open')

    # Assignment (to contractor)
    assigned_to = Column(GUID, ForeignKey('contractors.id', ondelete='SET NULL'))

    # Dates
    reported_date = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))

    # Resolution
    resolution_notes = Column(Text)
    tenant_accessible = Column(Boolean, default=True)

    # Cost
    estimated_cost = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))

    # ========================================================================
    # HUB-SPOKE FEDERATION METADATA
    # ========================================================================
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    sync_status = Column(String(20), default='synced')
    sync_error_message = Column(Text)
    created_by_hub = Column(Boolean, default=False, nullable=False)
    last_modified_by = Column(String(10), default='spoke')
    hub_override_at = Column(DateTime(timezone=True))
    hub_override_by = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="work_orders")
    building = relationship("Building", back_populates="work_orders")
    tenant = relationship("Tenant", back_populates="work_orders")
    contractor = relationship("Contractor", back_populates="work_orders")
    documents = relationship("Document", back_populates="work_order")
    events = relationship("WorkOrderEvent", back_populates="work_order", cascade="all, delete-orphan")
    tasks = relationship("WorkOrderTask", back_populates="work_order", cascade="all, delete-orphan", order_by="WorkOrderTask.sequence")
    materials = relationship("WorkOrderMaterial", back_populates="work_order", cascade="all, delete-orphan")
    maintenance_task = relationship("MaintenanceTask", back_populates="work_order", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'emergency')",
            name='valid_work_order_priority'
        ),
        CheckConstraint(
            "status IN ('open', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name='valid_work_order_status'
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')",
            name='valid_work_order_sync_status'
        ),
        CheckConstraint(
            "last_modified_by IN ('hub', 'spoke')",
            name='valid_work_order_last_modified_by'
        ),
        Index('idx_work_orders_unit_id', 'unit_id'),
        Index('idx_work_orders_building_id', 'building_id'),
        Index('idx_work_orders_status', 'status'),
        Index('idx_work_orders_priority', 'priority'),
        Index('idx_work_orders_assigned_to', 'assigned_to'),
        Index('idx_work_orders_hub_id', 'hub_id'),
        Index('idx_work_orders_client_id', 'client_id'),
        Index('idx_work_orders_sync_status', 'sync_status'),
        Index('idx_work_orders_synced_at', 'synced_at'),
    )


class WorkOrderTask(Base):
    """
    Work Order Tasks - Subtasks within a work order
    Tracks individual tasks with estimates and actuals
    """
    __tablename__ = "work_order_tasks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    work_order_id = Column(GUID, ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False)

    # Task details
    title = Column(String(255), nullable=False)
    notes = Column(Text)

    # Time tracking
    estimate_hours = Column(Numeric(10, 2))
    actual_hours = Column(Numeric(10, 2))

    # Ordering and status
    sequence = Column(Integer, default=0)
    status = Column(String(20), default='pending')

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    work_order = relationship("WorkOrder", back_populates="tasks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name='valid_task_status'
        ),
        Index('idx_work_order_tasks_work_order_id', 'work_order_id'),
        Index('idx_work_order_tasks_sequence', 'work_order_id', 'sequence'),
    )


class WorkOrderMaterial(Base):
    """
    Work Order Materials - Line items for parts and materials
    Tracks quantities and costs for materials used
    """
    __tablename__ = "work_order_materials"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    work_order_id = Column(GUID, ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False)

    # Material details
    item = Column(String(255), nullable=False)
    qty = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    extended_cost = Column(Numeric(10, 2), nullable=False)

    # Additional info
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    work_order = relationship("WorkOrder", back_populates="materials")

    __table_args__ = (
        Index('idx_work_order_materials_work_order_id', 'work_order_id'),
    )


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Company info
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20), nullable=False)
    secondary_phone = Column(String(20))
    website = Column(String(500))

    # Address
    address_line1 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))

    # Business details
    business_type = Column(String(100))
    license_number = Column(String(100))
    insurance_provider = Column(String(255))
    insurance_policy_number = Column(String(100))
    insurance_expires_at = Column(Date)

    # Specialties
    trade = Column(String(100))  # Legacy field, use categories
    specialties = Column(ARRAY(Text))  # Legacy field, use specialty_services
    categories = Column(ARRAY(Text), default=list)  # e.g., ["plumbing", "HVAC"]
    specialty_services = Column(ARRAY(Text), default=list)  # Detailed services

    # Pricing
    pricing_model = Column(String(20), default='hourly')  # hourly, flat_rate, quote
    hourly_rate = Column(Numeric(10, 2))
    emergency_rate = Column(Numeric(10, 2))
    minimum_charge = Column(Numeric(10, 2))
    travel_fee = Column(Numeric(10, 2))

    # Availability
    available_weekdays = Column(Boolean, default=True)
    available_weekends = Column(Boolean, default=False)
    available_24_7 = Column(Boolean, default=False)
    service_area_radius_miles = Column(Integer)

    # Status
    approval_status = Column(String(20), default='approved')  # pending, approved, inactive
    available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)  # Legacy field

    # Performance metrics
    average_rating = Column(Numeric(3, 2), default=0)
    total_jobs = Column(Integer, default=0)
    total_jobs_completed = Column(Integer, default=0)
    on_time_rate = Column(Numeric(5, 2))  # Percentage
    response_time_hours = Column(Integer)
    last_job_date = Column(Date)

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    work_orders = relationship("WorkOrder", back_populates="contractor")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="contractor")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="contractor")
    # Contractor work examples/portfolio (from models_contractor_labor.py)
    work_examples = relationship("ContractorWorkExample", back_populates="contractor", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'inactive', 'rejected')",
            name='valid_contractor_approval_status'
        ),
        CheckConstraint(
            "pricing_model IN ('hourly', 'flat_rate', 'quote')",
            name='valid_pricing_model'
        ),
        Index('idx_contractors_approval_status', 'approval_status'),
        Index('idx_contractors_available', 'available'),
        Index('idx_contractors_categories', 'categories', postgresql_using='gin'),
    )


class WorkOrderEvent(Base):
    """Event history tracking for work orders"""
    __tablename__ = "work_order_events"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    work_order_id = Column(GUID, ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)  # status_change, assignment, comment, update, etc.
    old_value = Column(String(255))
    new_value = Column(String(255))

    # Who made the change
    created_by = Column(String(255))  # Username or contractor name
    created_by_type = Column(String(20))  # staff, contractor, tenant, system

    # Additional context
    notes = Column(Text)
    event_metadata = Column(JSONB)  # Additional event data

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    work_order = relationship("WorkOrder", back_populates="events")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'status_change', 'assignment', 'reassignment', 'comment', 'cost_update', 'priority_change', 'completed', 'cancelled')",
            name='valid_event_type'
        ),
        CheckConstraint(
            "created_by_type IN ('staff', 'contractor', 'tenant', 'system')",
            name='valid_created_by_type'
        ),
        Index('idx_work_order_events_work_order_id', 'work_order_id'),
        Index('idx_work_order_events_created_at', 'created_at'),
        Index('idx_work_order_events_event_type', 'event_type'),
    )


# ============================================================================
# IOT INTEGRATION
# ============================================================================

class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'))

    # Device identification
    entity_id = Column(String(255), nullable=False, unique=True)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)
    device_category = Column(String(50))

    # Status
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    battery_level = Column(Integer)

    # Home Assistant integration
    ha_instance_id = Column(String(100))
    mqtt_topic = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="iot_devices")
    building = relationship("Building", back_populates="iot_devices")
    sensor_readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_iot_devices_unit_id', 'unit_id'),
        Index('idx_iot_devices_entity_id', 'entity_id'),
        Index('idx_iot_devices_device_type', 'device_type'),
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(GUID, ForeignKey('iot_devices.id', ondelete='CASCADE'), nullable=False)

    # Reading data
    metric = Column(String(50), nullable=False)
    value = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(20))

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    device = relationship("IoTDevice", back_populates="sensor_readings")

    __table_args__ = (
        Index('idx_sensor_readings_device_timestamp', 'device_id', 'timestamp'),
        Index('idx_sensor_readings_timestamp', 'timestamp'),
    )


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'), nullable=False)

    # Access details
    entity_id = Column(String(255), nullable=False)
    access_type = Column(String(50), nullable=False)
    user_name = Column(String(255))

    # Event details
    event_type = Column(String(20), nullable=False)
    success = Column(Boolean, default=True)

    # Code/credential used
    code_used = Column(String(50))

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="access_logs")

    __table_args__ = (
        Index('idx_access_logs_unit_timestamp', 'unit_id', 'timestamp'),
        Index('idx_access_logs_timestamp', 'timestamp'),
    )


class Alert(Base):
    """
    Alerts and Incidents
    Aggregates alerts from Home Assistant and MQTT events for monitoring and response
    """
    __tablename__ = "alerts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id'))

    # Alert classification
    severity = Column(String(20), nullable=False)  # info, warning, critical
    source = Column(String(50), nullable=False)  # home_assistant, mqtt, system
    category = Column(String(50), nullable=False)  # leak, fire, security, hvac, etc.

    # Alert details
    message = Column(Text, nullable=False)
    entity_id = Column(String(255))  # HA entity that triggered

    # Timestamps
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime(timezone=True))

    # Status
    status = Column(String(20), default='open')  # open, acknowledged, resolved

    # Additional context
    alert_metadata = Column(JSONB)  # Additional context

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    hub = relationship("PropertyEdgeNode")

    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name='valid_alert_severity'),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name='valid_alert_status'),
        Index('idx_alerts_hub_id', 'hub_id'),
        Index('idx_alerts_severity', 'severity'),
        Index('idx_alerts_occurred_at', 'occurred_at'),
        Index('idx_alerts_status', 'status'),
    )


class SupportTicket(Base):
    """
    Support Tickets for Proactive Outreach Workflow
    Auto-created from critical alerts or manually created
    """
    __tablename__ = "support_tickets"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('clients.id'))  # For SomniFamily
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id'))
    alert_id = Column(GUID, ForeignKey('alerts.id'))  # Triggering alert (if auto-created)

    # Ticket classification
    category = Column(String(50))  # leak, hvac, security, etc.
    severity = Column(String(20))  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Status tracking
    status = Column(String(20), default='open')  # open, in_progress, resolved, closed
    priority = Column(String(20))  # follows severity

    # SLA tracking
    sla_due_at = Column(DateTime(timezone=True))
    sla_breach = Column(Boolean, default=False)

    # Assignment
    assigned_to = Column(String(255))  # Staff member
    assigned_at = Column(DateTime(timezone=True))

    # Resolution
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)

    # Client communication
    client_notified = Column(Boolean, default=False)
    client_notified_at = Column(DateTime(timezone=True))

    # Quote/Estimate fields (for service requests per spec §3.4, §5.8)
    quote_requested = Column(Boolean, default=False)
    quote_amount = Column(Numeric(10, 2))
    quote_notes = Column(Text)
    quote_provided_at = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Client")
    hub = relationship("PropertyEdgeNode")
    alert = relationship("Alert")

    __table_args__ = (
        CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed')", name='valid_ticket_status'),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='valid_ticket_severity'),
        Index('idx_support_tickets_client_id', 'client_id'),
        Index('idx_support_tickets_status', 'status'),
        Index('idx_support_tickets_severity', 'severity'),
        Index('idx_support_tickets_sla_due_at', 'sla_due_at'),
        Index('idx_support_tickets_quote_requested', 'quote_requested'),
    )


# ============================================================================
# AUTOMATION RULES
# ============================================================================

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'))

    # Rule definition
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Trigger
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSONB, nullable=False)

    # Conditions
    conditions = Column(JSONB)

    # Actions
    actions = Column(JSONB, nullable=False)

    # Status
    is_enabled = Column(Boolean, default=True)

    # Execution tracking
    last_triggered = Column(DateTime(timezone=True))
    trigger_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="automation_rules")


# ============================================================================
# UTILITIES & BILLING
# ============================================================================

class UtilityBill(Base):
    __tablename__ = "utility_bills"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'), nullable=False)

    # Billing period
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)

    # Utility type
    utility_type = Column(String(50), nullable=False)

    # Usage & cost
    usage_amount = Column(Numeric(12, 4))
    usage_unit = Column(String(20))
    base_charge = Column(Numeric(10, 2), default=0)
    usage_charge = Column(Numeric(10, 2), nullable=False)
    total_charge = Column(Numeric(10, 2), nullable=False)

    # Data source
    source = Column(String(50), default='sensor')

    # Invoice integration
    invoice_id = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="utility_bills")

    __table_args__ = (
        CheckConstraint(
            "utility_type IN ('electric', 'water', 'gas', 'trash', 'internet')",
            name='valid_utility_type'
        ),
    )


# ============================================================================
# DOCUMENTS
# ============================================================================

class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='CASCADE'))
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'))
    lease_id = Column(GUID, ForeignKey('leases.id', ondelete='CASCADE'))
    work_order_id = Column(GUID, ForeignKey('work_orders.id', ondelete='CASCADE'))

    # Document details
    document_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Storage
    paperless_document_id = Column(Integer)
    minio_object_key = Column(String(500))
    file_url = Column(Text)

    # Metadata
    file_size_bytes = Column(BigInteger)
    mime_type = Column(String(100))
    upload_date = Column(Date, server_default=func.current_date())
    uploaded_by = Column(String(255))

    # DocuSeal integration for digital signatures
    docuseal_submission_id = Column(Integer)
    docuseal_template_id = Column(Integer)
    signing_status = Column(String(50), default='draft')  # draft, pending, partially_signed, signed, cancelled, expired
    signed_at = Column(DateTime(timezone=True))
    docuseal_metadata = Column(JSONB)  # Additional metadata like signers, fields, etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="documents")
    unit = relationship("Unit", back_populates="documents")
    tenant = relationship("Tenant", back_populates="documents")
    lease = relationship("Lease", back_populates="documents")
    work_order = relationship("WorkOrder", back_populates="documents")

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('lease', 'inspection', 'receipt', 'notice', 'photo', 'insurance', 'deed', 'work_order_completion', 'move_in_checklist', 'move_out_checklist', 'other')",
            name='valid_document_type'
        ),
    )

# ============================================================================
# SMART HOME AS A SERVICE (SHaaS) MODELS
# ============================================================================

class ServicePackage(Base):
    """Tiered smart home service offerings (Basic/Premium/Enterprise) with K8s stack definitions"""
    __tablename__ = "service_packages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # ========================================================================
    # 3-TIER ARCHITECTURE FIELDS (Stack Definition)
    # ========================================================================
    # Tier Targeting: Which hub types can use this package
    target_tier = Column(String(20), default='tier_3')  # tier_2 | tier_3 | both

    # Stack Definition (Kubernetes manifests to deploy)
    # included_services: ["home-assistant", "frigate", "tailscale", "music-assistant"]
    # service_versions: {"home-assistant": "2024.1", "frigate": "0.13"}
    service_versions = Column(JSONB)  # Map of service → version

    # Manifest References (GitOps integration)
    manifest_repo_url = Column(String(500))  # Git repo URL with stack manifests
    manifest_path = Column(String(500))  # Path in repo to this stack's manifests

    # ========================================================================
    # EXISTING FIELDS
    # ========================================================================
    # Package details
    name = Column(String(100), nullable=False)  # e.g., "Property Manager Basic", "Residential Premium"
    description = Column(Text)

    # Pricing
    monthly_fee = Column(Numeric(10, 2), nullable=False)
    installation_fee = Column(Numeric(10, 2), default=0)
    annual_discount_percent = Column(Numeric(5, 2), default=0)  # e.g., 10.00 = 10% off annual

    # Service inclusions
    included_services = Column(JSONB)  # ["home-assistant", "frigate", "tailscale"] (service names)
    included_device_count = Column(Integer, default=0)
    sla_response_time_hours = Column(Integer, default=48)  # Support response SLA

    # Features
    features = Column(JSONB)  # Detailed feature list for UI display
    active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    service_contracts = relationship("ServiceContract", back_populates="package")

    __table_args__ = (
        CheckConstraint(
            "target_tier IN ('tier_2', 'tier_3', 'both')",
            name='valid_target_tier'
        ),
        Index('idx_service_packages_active', 'active'),
        Index('idx_service_packages_target_tier', 'target_tier'),
    )


class ServiceContract(Base):
    """Smart home service contracts (like leases, but for services)"""
    __tablename__ = "service_contracts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    package_id = Column(GUID, ForeignKey('service_packages.id', ondelete='RESTRICT'), nullable=False)
    
    # Contract terms
    contract_type = Column(String(20), default='monthly')  # monthly, annual, project
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # null for ongoing monthly
    auto_renew = Column(Boolean, default=True)
    
    # Pricing
    monthly_fee = Column(Numeric(10, 2), nullable=False)
    installation_fee = Column(Numeric(10, 2), default=0)
    
    # Status
    status = Column(String(20), default='draft')  # draft, active, paused, cancelled, completed
    installation_completed = Column(Boolean, default=False)
    installation_date = Column(Date)
    
    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    client = relationship("Tenant", back_populates="service_contracts")
    property = relationship("Property")
    package = relationship("ServicePackage", back_populates="service_contracts")
    installations = relationship("Installation", back_populates="contract", cascade="all, delete-orphan")
    devices = relationship("SmartDevice", back_populates="service_contract")
    
    __table_args__ = (
        CheckConstraint(
            "contract_type IN ('monthly', 'annual', 'project')",
            name='valid_contract_type'
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'cancelled', 'completed')",
            name='valid_service_contract_status'
        ),
        Index('idx_service_contracts_client_id', 'client_id'),
        Index('idx_service_contracts_property_id', 'property_id'),
        Index('idx_service_contracts_status', 'status'),
        Index('idx_service_contracts_start_date', 'start_date'),
    )


class Installation(Base):
    """Installation project tracking for smart home deployments"""
    __tablename__ = "installations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    contract_id = Column(GUID, ForeignKey('service_contracts.id', ondelete='CASCADE'), nullable=False)
    
    # Installation details
    status = Column(String(20), default='scheduled')  # scheduled, in_progress, completed, cancelled
    scheduled_date = Column(Date, nullable=False)
    completion_date = Column(Date)
    installer_id = Column(GUID)  # Staff or contractor
    installer_name = Column(String(255))
    
    # Devices
    devices_to_install = Column(JSONB)  # List of planned devices
    devices_installed = Column(JSONB)  # List of actually installed device IDs
    
    # Project tracking
    installation_notes = Column(Text)
    completion_certificate_id = Column(GUID, ForeignKey('documents.id'))
    
    # Costs
    total_cost = Column(Numeric(10, 2), default=0)
    labor_hours = Column(Numeric(5, 2), default=0)
    labor_cost = Column(Numeric(10, 2), default=0)
    materials_cost = Column(Numeric(10, 2), default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    client = relationship("Tenant")
    property = relationship("Property")
    contract = relationship("ServiceContract", back_populates="installations")
    completion_certificate = relationship("Document", foreign_keys=[completion_certificate_id])
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'completed', 'cancelled')",
            name='valid_installation_status'
        ),
        Index('idx_installations_client_id', 'client_id'),
        Index('idx_installations_property_id', 'property_id'),
        Index('idx_installations_status', 'status'),
        Index('idx_installations_scheduled_date', 'scheduled_date'),
    )


class SmartDevice(Base):
    """Smart device inventory across all managed properties (auto-synced from Home Assistant)"""
    __tablename__ = "smart_devices"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    client_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    service_contract_id = Column(GUID, ForeignKey('service_contracts.id', ondelete='SET NULL'))

    # ========================================================================
    # HOME ASSISTANT SYNC FIELDS (3-Tier Architecture)
    # ========================================================================
    # Sync Source: Devices are primarily synced from HA instances
    sync_source = Column(String(20), default='home_assistant')  # home_assistant | manual (legacy)
    synced_from_hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='SET NULL'))  # Which Tier 2/3 hub
    last_synced_at = Column(DateTime(timezone=True))

    # Home Assistant Entity Data
    home_assistant_entity_id = Column(String(255))  # e.g., "light.living_room"
    ha_domain = Column(String(50))  # light, switch, sensor, climate, lock, etc.
    ha_state = Column(String(100))  # Current state from HA (on, off, temperature value, etc.)
    ha_attributes = Column(JSONB)  # Full HA attributes JSON blob

    # Device Name (from HA friendly_name or device_name)
    device_name = Column(String(255))

    # ========================================================================
    # EXISTING FIELDS
    # ========================================================================
    # Device identification
    device_type = Column(String(50), nullable=False)  # sensor, switch, camera, hub, thermostat, lock, etc.
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(100))

    # Installation info
    installation_date = Column(Date)
    warranty_expiration = Column(Date)
    firmware_version = Column(String(50))

    # Integration
    mqtt_topic = Column(String(255))
    ha_entity_id = Column(String(255))  # DEPRECATED: Use home_assistant_entity_id
    edge_node_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='SET NULL'))  # DEPRECATED: Use synced_from_hub_id

    # Status
    status = Column(String(20), default='active')  # active, inactive, maintenance, failed, retired
    health_status = Column(String(20), default='healthy')  # healthy, warning, critical, unknown
    last_seen = Column(DateTime(timezone=True))
    last_heartbeat = Column(DateTime(timezone=True))

    # Battery and Signal (MQTT/heartbeat data)
    battery_level = Column(Integer)
    signal_strength = Column(Integer)

    # Physical location
    location = Column(String(255))  # e.g., "Living Room - North Wall"
    ip_address = Column(INET)
    mac_address = Column(String(50))

    # Lifecycle
    replacement_due = Column(Date)
    retired_date = Column(Date)
    retirement_reason = Column(Text)

    # Notes
    location_description = Column(String(255))  # e.g., "Living Room - North Wall"
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property")
    client = relationship("Tenant")
    service_contract = relationship("ServiceContract", back_populates="devices")
    edge_node = relationship("PropertyEdgeNode", foreign_keys=[edge_node_id])  # DEPRECATED: Legacy relationship
    synced_from_hub = relationship("PropertyEdgeNode", back_populates="devices", foreign_keys=[synced_from_hub_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance', 'failed', 'retired')",
            name='valid_device_status'
        ),
        CheckConstraint(
            "health_status IN ('healthy', 'warning', 'critical', 'unknown')",
            name='valid_device_health_status'
        ),
        CheckConstraint(
            "sync_source IN ('home_assistant', 'manual')",
            name='valid_sync_source'
        ),
        Index('idx_smart_devices_property_id', 'property_id'),
        Index('idx_smart_devices_client_id', 'client_id'),
        Index('idx_smart_devices_status', 'status'),
        Index('idx_smart_devices_health_status', 'health_status'),
        Index('idx_smart_devices_ha_entity_id', 'ha_entity_id'),
        Index('idx_smart_devices_home_assistant_entity_id', 'home_assistant_entity_id'),
        Index('idx_smart_devices_synced_from_hub_id', 'synced_from_hub_id'),
        Index('idx_smart_devices_sync_source', 'sync_source'),
        Index('idx_smart_devices_last_seen', 'last_seen'),
        Index('idx_smart_devices_last_synced_at', 'last_synced_at'),
    )


class PropertyEdgeNode(Base):
    """Property edge nodes (Tier 2/3 Kubernetes clusters managing smart homes)"""
    __tablename__ = "property_edge_nodes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Parent Hub Linkage (for residential hubs in multi-unit buildings)
    # Residential hubs (apartments) reference their parent property hub
    parent_hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='SET NULL'), nullable=True)

    # ========================================================================
    # HUB TYPE FIELDS
    # ========================================================================
    # Hub Type: PROPERTY_HUB (multi-unit buildings) | RESIDENTIAL (single-family homes/apartments)
    # Replaces the confusing tier_0/tier_2/tier_3 nomenclature
    hub_type = Column(String(30), default='RESIDENTIAL')  # PROPERTY_HUB | RESIDENTIAL

    # Sync Status (device sync from HA to Tier 1)
    sync_status = Column(String(20), default='never_synced')  # synced | syncing | error | never_synced
    sync_error_message = Column(Text)

    # Deployment Info (what stack is deployed)
    deployed_stack = Column(String(50))  # 'property_manager' | 'residential'
    manifest_version = Column(String(255))  # Git commit SHA or version tag

    # Fleet Management
    managed_by_tier1 = Column(Boolean, default=True)
    auto_update_enabled = Column(Boolean, default=True)

    # API Authentication (for Tier 1 → Tier 2/3 communication)
    api_token_hash = Column(String(500))  # Bcrypt hashed token for hub auth
    tailscale_ip = Column(INET)  # Tailscale mesh IP for secure communication

    # ========================================================================
    # EXISTING FIELDS
    # ========================================================================
    # Node details
    node_type = Column(String(30), default='home_assistant')  # home_assistant, mqtt, custom
    hostname = Column(String(255), nullable=False)
    ip_address = Column(INET)
    tailscale_hostname = Column(String(255))

    # Authentication
    api_token = Column(String(500))  # Encrypted HA token
    api_url = Column(String(500))

    # MQTT configuration
    mqtt_broker_host = Column(String(255))
    mqtt_broker_port = Column(Integer, default=1883)
    mqtt_topics = Column(JSONB)  # Subscribed topics

    # Status
    status = Column(String(20), default='offline')  # online, offline, error, maintenance
    last_heartbeat = Column(DateTime(timezone=True))
    last_sync = Column(DateTime(timezone=True))

    # Metrics
    firmware_version = Column(String(50))
    device_count = Column(Integer, default=0)
    automation_count = Column(Integer, default=0)
    uptime_hours = Column(Integer, default=0)

    # Resource usage
    resource_usage = Column(JSONB)  # {cpu: 25, memory: 40, disk: 60} (percentages)

    # ========================================================================
    # SOMNI CUSTOM COMPONENTS (Home Assistant Integrations)
    # ========================================================================
    # Tracks which Somni custom HA components are installed on this hub
    # Format: {"somni_lights": true, "somni_occupancy": false, ...}
    installed_somni_components = Column(JSONB, default=dict)  # Component name → installed status

    # Last component install/uninstall operation
    last_component_sync_id = Column(GUID, ForeignKey('component_syncs.id', ondelete='SET NULL'))
    last_component_sync_at = Column(DateTime(timezone=True))

    # ========================================================================
    # AUTOMATIC DEPLOYMENT FIELDS
    # ========================================================================
    # Deployment Status Tracking
    deployment_status = Column(String(30), default='pending')  # pending | in_progress | deployed | failed | unknown
    deployment_started_at = Column(DateTime(timezone=True))
    deployment_completed_at = Column(DateTime(timezone=True))
    deployment_error_message = Column(Text)
    deployment_progress_percent = Column(Integer, default=0)
    deployment_current_step = Column(String(255))

    # SSH Configuration (for Tier 2/3 k3s deployment)
    deployment_ssh_host = Column(String(255))  # SSH target host
    deployment_ssh_port = Column(Integer, default=22)
    deployment_ssh_user = Column(String(100))
    deployment_ssh_key_encrypted = Column(Text)  # Fernet-encrypted SSH private key

    # Home Assistant Configuration (for Tier 0 component deployment)
    deployment_ha_url = Column(String(500))  # HA instance URL
    deployment_ha_token_hash = Column(String(500))  # Bcrypt hashed HA long-lived token

    # Deployment Details
    deployed_components = Column(JSONB)  # List of installed components: ["ha", "emqx", "tailscale", "monitoring"]
    deployment_logs = Column(Text)  # Full deployment log for troubleshooting
    deployment_manifest_version = Column(String(100))  # Git commit SHA or version tag of deployed manifests

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property")
    devices = relationship("SmartDevice", back_populates="synced_from_hub", foreign_keys="SmartDevice.synced_from_hub_id")
    fleet_deployments = relationship("FleetDeployment", back_populates="target_hub")
    device_syncs = relationship("DeviceSync", back_populates="source_hub")

    # Parent/Child Hub Relationships (for multi-unit buildings)
    parent = relationship("PropertyEdgeNode", remote_side=[id], foreign_keys=[parent_hub_id], backref="children")

    __table_args__ = (
        CheckConstraint(
            "node_type IN ('home_assistant', 'mqtt', 'custom')",
            name='valid_node_type'
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'error', 'maintenance')",
            name='valid_edge_node_status'
        ),
        CheckConstraint(
            "hub_type IN ('PROPERTY_HUB', 'RESIDENTIAL')",
            name='valid_hub_type'
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'syncing', 'error', 'never_synced')",
            name='valid_sync_status'
        ),
        CheckConstraint(
            "deployment_status IN ('pending', 'in_progress', 'deployed', 'failed', 'unknown')",
            name='valid_deployment_status'
        ),
        Index('idx_property_edge_nodes_property_id', 'property_id'),
        Index('idx_property_edge_nodes_status', 'status'),
        Index('idx_property_edge_nodes_last_heartbeat', 'last_heartbeat'),
        Index('idx_property_edge_nodes_hub_type', 'hub_type'),
        Index('idx_property_edge_nodes_sync_status', 'sync_status'),
        Index('idx_property_edge_nodes_parent_hub_id', 'parent_hub_id'),
    )


# ============================================================================
# FLEET MANAGEMENT (3-Tier Architecture)
# ============================================================================

class FleetDeployment(Base):
    """Track deployments of service packages to Tier 2/3 hubs"""
    __tablename__ = "fleet_deployments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Target Hub
    target_hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'), nullable=False)
    target_hub_type = Column(String(30), nullable=False)  # PROPERTY_HUB | RESIDENTIAL

    # Deployment Info
    service_package_id = Column(GUID, ForeignKey('service_packages.id', ondelete='RESTRICT'), nullable=False)
    manifest_version = Column(String(255), nullable=False)  # Git commit SHA
    deployment_status = Column(String(20), default='pending')  # pending | deploying | success | failed

    # Timing
    initiated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Results
    deployment_log = Column(Text)  # Console output from deployment
    error_message = Column(Text)

    # Metadata
    initiated_by = Column(String(255))  # Username who triggered deployment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    target_hub = relationship("PropertyEdgeNode", back_populates="fleet_deployments")
    service_package = relationship("ServicePackage")

    __table_args__ = (
        CheckConstraint(
            "deployment_status IN ('pending', 'deploying', 'success', 'failed')",
            name='valid_deployment_status'
        ),
        CheckConstraint(
            "target_hub_type IN ('PROPERTY_HUB', 'RESIDENTIAL')",
            name='valid_target_hub_type'
        ),
        Index('idx_fleet_deployments_target_hub_id', 'target_hub_id'),
        Index('idx_fleet_deployments_service_package_id', 'service_package_id'),
        Index('idx_fleet_deployments_status', 'deployment_status'),
        Index('idx_fleet_deployments_initiated_at', 'initiated_at'),
    )


class DeviceSync(Base):
    """Track device sync operations from Tier 2/3 hubs to Master Hub"""
    __tablename__ = "device_syncs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Source Hub (Tier 2 or 3)
    source_hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'), nullable=False)

    # Sync Info
    sync_started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sync_completed_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='success')  # success | partial | failed

    # Results
    devices_discovered = Column(Integer, default=0)
    devices_added = Column(Integer, default=0)
    devices_updated = Column(Integer, default=0)
    devices_removed = Column(Integer, default=0)

    # Errors
    error_message = Column(Text)
    error_details = Column(JSONB)  # Structured error data

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    source_hub = relationship("PropertyEdgeNode", back_populates="device_syncs")

    __table_args__ = (
        CheckConstraint(
            "sync_status IN ('success', 'partial', 'failed')",
            name='valid_sync_status'
        ),
        Index('idx_device_syncs_source_hub_id', 'source_hub_id'),
        Index('idx_device_syncs_sync_started_at', 'sync_started_at'),
        Index('idx_device_syncs_sync_status', 'sync_status'),
    )


class ComponentSync(Base):
    """Track component sync operations to Tier 0/1/2 hubs"""
    __tablename__ = "component_syncs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Target Hub (can be PropertyEdgeNode or external hub)
    target_hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'))
    target_hub_host = Column(String(255), nullable=False)  # SSH host or Tailscale hostname
    target_hub_type = Column(String(30), nullable=False)  # PROPERTY_HUB | RESIDENTIAL

    # Sync method
    sync_method = Column(String(20), default='rsync')  # rsync | gitops

    # Sync Info
    sync_started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sync_completed_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='in_progress')  # in_progress | success | partial_success | failed

    # Components synced
    components_requested = Column(JSONB)  # List of component names requested
    components_synced = Column(JSONB)  # List of component names successfully synced
    addons_requested = Column(JSONB)  # List of addon names requested
    addons_synced = Column(JSONB)  # List of addon names successfully synced

    # Results
    sync_logs = Column(Text)  # Full sync logs
    error_messages = Column(JSONB)  # Structured error data

    # GitOps specific fields
    gitops_repo_url = Column(String(500))  # For GitOps deployments
    gitops_commit_sha = Column(String(255))  # Git commit SHA
    gitops_branch = Column(String(255))  # Git branch

    # Restart info
    ha_restart_initiated = Column(Boolean, default=False)
    ha_restart_successful = Column(Boolean)

    # Initiated by
    initiated_by = Column(String(255))  # Username who triggered sync

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    target_hub = relationship("PropertyEdgeNode", foreign_keys=[target_hub_id])

    __table_args__ = (
        CheckConstraint(
            "sync_status IN ('in_progress', 'success', 'partial_success', 'failed')",
            name='valid_component_sync_status'
        ),
        CheckConstraint(
            "target_hub_type IN ('PROPERTY_HUB', 'RESIDENTIAL')",
            name='valid_component_sync_hub_type'
        ),
        CheckConstraint(
            "sync_method IN ('rsync', 'gitops')",
            name='valid_sync_method'
        ),
        Index('idx_component_syncs_target_hub_id', 'target_hub_id'),
        Index('idx_component_syncs_sync_started_at', 'sync_started_at'),
        Index('idx_component_syncs_sync_status', 'sync_status'),
        Index('idx_component_syncs_target_hub_type', 'target_hub_type'),
        Index('idx_component_syncs_sync_method', 'sync_method'),
    )


# ============================================================================
# CLIENT MANAGEMENT (Somni Intelligent Living as a Service)
# ============================================================================

class Client(Base):
    """Clients for Somni's Intelligent Living as a Service - Three-tier customer model with comprehensive onboarding"""
    __tablename__ = "clients"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Basic Information
    name = Column(String(255), nullable=False)
    tier = Column(String(20), nullable=False)  # tier_0 | tier_1 | tier_2
    client_type = Column(String(20), nullable=False, default='multi-unit')  # multi-unit | single-family

    # Contact Information (Original)
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(100), default='USA')

    # Primary Contact Information
    primary_contact_name = Column(String(255))
    primary_contact_title = Column(String(100))
    primary_contact_phone = Column(String(20))
    primary_contact_email = Column(String(255))

    # Secondary Contact Information
    secondary_contact_name = Column(String(255))
    secondary_contact_title = Column(String(100))
    secondary_contact_phone = Column(String(20))
    secondary_contact_email = Column(String(255))

    # Property Information
    property_name = Column(String(255))
    property_address_line1 = Column(String(255))
    property_address_line2 = Column(String(255))
    property_city = Column(String(100))
    property_state = Column(String(50))
    property_zip_code = Column(String(20))
    property_country = Column(String(100), default='USA')

    # Property Details
    property_type = Column(String(50))  # single_family | multi_unit | commercial | mixed_use | other
    property_unit_count = Column(Integer)
    property_year_built = Column(Integer)
    property_square_feet = Column(Integer)
    property_description = Column(Text)

    # Onboarding Workflow
    onboarding_stage = Column(String(50), default='initial', nullable=False)  # initial | discovery | assessment | proposal | contract | deployment | completed
    onboarding_step = Column(Integer, default=1, nullable=False)
    onboarding_progress_percent = Column(Integer, default=0, nullable=False)
    discovery_call_scheduled_at = Column(DateTime(timezone=True))
    discovery_call_completed_at = Column(DateTime(timezone=True))
    initial_assessment_completed = Column(Boolean, default=False, nullable=False)

    # Initial Transcript/Notes
    discovery_call_transcript = Column(Text)
    initial_notes = Column(Text)
    special_requirements = Column(Text)

    # Communication Preferences
    preferred_contact_method = Column(String(20), default='email')  # email | phone | sms | any
    preferred_contact_time = Column(String(50))
    timezone = Column(String(50), default='America/New_York')

    # Billing Information
    subscription_plan = Column(String(100))
    monthly_fee = Column(Numeric(10, 2))
    billing_status = Column(String(20), default='active')  # active | suspended | cancelled | past_due

    # SLA Information
    support_level = Column(String(50))  # self-managed | managed | enterprise
    response_time_hours = Column(Integer)  # SLA response time in hours
    uptime_guarantee = Column(Numeric(5, 2))  # e.g., 99.00 for 99% uptime

    # Tier 2 Enterprise Specific (Property Managers/Landlords)
    is_landlord_client = Column(Boolean, default=False)
    rent_collection_fee_percent = Column(Numeric(5, 2))  # e.g., 8.00 for 8% fee

    # Relationships to Infrastructure
    # Tier 1 and Tier 2 have 1:1 with PropertyEdgeNode
    edge_node_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='SET NULL'))
    # Tier 2 Type A (landlord managing rental property) links to Property
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='SET NULL'))

    # Account Status
    status = Column(String(20), default='active')  # active | suspended | cancelled | churned
    onboarding_completed = Column(Boolean, default=False)
    onboarded_at = Column(DateTime(timezone=True))
    churned_at = Column(DateTime(timezone=True))
    churn_reason = Column(Text)

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    edge_node = relationship("PropertyEdgeNode")
    property = relationship("Property")
    family_subscription = relationship("FamilySubscription", back_populates="client", uselist=False)
    media = relationship("ClientMedia", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "tier IN ('tier_0', 'tier_1', 'tier_2')",
            name='valid_client_tier'
        ),
        CheckConstraint(
            "client_type IN ('multi-unit', 'single-family')",
            name='valid_client_type'
        ),
        CheckConstraint(
            "billing_status IN ('active', 'suspended', 'cancelled', 'past_due')",
            name='valid_billing_status'
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'cancelled', 'churned')",
            name='valid_client_status'
        ),
        Index('idx_clients_tier', 'tier'),
        Index('idx_clients_client_type', 'client_type'),
        Index('idx_clients_status', 'status'),
        Index('idx_clients_billing_status', 'billing_status'),
        Index('idx_clients_email', 'email'),
        Index('idx_clients_edge_node_id', 'edge_node_id'),
        Index('idx_clients_property_id', 'property_id'),
    )


class ClientMedia(Base):
    """Client portfolio media files - photos, videos, floorplans, 3D models"""
    __tablename__ = "client_media"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)

    # Media Classification
    media_type = Column(String(20), nullable=False)  # photo | video | floorplan | 3d_model | document | other
    media_category = Column(String(50), nullable=False)  # property_exterior | property_interior | unit_example | amenities | floorplan | site_plan | 3d_model | permit | inspection | other
    file_name = Column(String(500), nullable=False)
    original_file_name = Column(String(500), nullable=False)
    file_extension = Column(String(10), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)

    # Storage
    minio_bucket = Column(String(100), nullable=False)
    minio_object_key = Column(String(500), nullable=False)
    minio_url = Column(Text)
    cdn_url = Column(Text)

    # Thumbnails (for images/videos)
    thumbnail_minio_key = Column(String(500))
    thumbnail_url = Column(Text)

    # Metadata
    title = Column(String(255))
    description = Column(Text)
    tags = Column(ARRAY(String))
    captured_date = Column(Date)

    # Image/Video specific metadata
    width = Column(Integer)
    height = Column(Integer)
    duration_seconds = Column(Integer)
    frame_rate = Column(Numeric(10, 2))

    # Document specific metadata (floorplans, 3D files)
    page_count = Column(Integer)
    document_version = Column(String(50))

    # 3D Model specific metadata
    model_format = Column(String(10))  # GLB, USDZ, PLY, 3DS, OBJ, etc.
    polygon_count = Column(Integer)
    model_dimensions = Column(JSONB)  # {width: X, height: Y, depth: Z, unit: "meters"}

    # Processing Status
    processing_status = Column(String(20), default='pending', nullable=False)  # pending | processing | completed | failed
    processing_error = Column(Text)
    thumbnail_generated = Column(Boolean, default=False, nullable=False)

    # Upload Information
    uploaded_by = Column(String(255))
    upload_source = Column(String(50), default='web_ui', nullable=False)  # web_ui | mobile_app | api | email | bulk_import
    upload_ip_address = Column(INET)

    # Visibility
    is_public = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    client = relationship("Client", back_populates="media")

    __table_args__ = (
        CheckConstraint(
            "media_type IN ('photo', 'video', 'floorplan', '3d_model', 'document', 'other')",
            name='valid_media_type'
        ),
        CheckConstraint(
            "media_category IN ('property_exterior', 'property_interior', 'unit_example', 'amenities', 'floorplan', 'site_plan', '3d_model', 'permit', 'inspection', 'other')",
            name='valid_media_category'
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name='valid_processing_status'
        ),
        CheckConstraint(
            "upload_source IN ('web_ui', 'mobile_app', 'api', 'email', 'bulk_import')",
            name='valid_upload_source'
        ),
        CheckConstraint('file_size_bytes > 0', name='positive_file_size'),
        Index('idx_client_media_client_id', 'client_id'),
        Index('idx_client_media_media_type', 'media_type'),
        Index('idx_client_media_media_category', 'media_category'),
        Index('idx_client_media_processing_status', 'processing_status'),
        Index('idx_client_media_created_at', 'created_at'),
        Index('idx_client_media_deleted_at', 'deleted_at'),
        Index('idx_client_media_tags', 'tags', postgresql_using='gin'),
    )


# ============================================================================
# SERVICE CATALOG (One-click Service Deployment)
# ============================================================================

class ServiceDeployment(Base):
    """Track one-click service deployments to Tier 1/2 client K3s clusters"""
    __tablename__ = "service_deployments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Target Client (Tier 1/2 hub)
    client_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'), nullable=False)

    # Service Information
    service_id = Column(String(100), nullable=False)  # e.g., "portainer", "grafana", "frigate"
    service_name = Column(String(255), nullable=False)  # Human-readable name

    # Deployment Status
    deployment_status = Column(String(30), default='pending')  # pending | deploying | deployed | failed | uninstalling | uninstalled

    # Timing
    deployed_at = Column(DateTime(timezone=True))
    uninstalled_at = Column(DateTime(timezone=True))

    # GitOps Integration
    manifest_version = Column(String(255))  # Git commit SHA of manifest
    git_commit_sha = Column(String(255))  # Git commit that added this service
    gitops_repo_url = Column(String(500))  # Client's GitOps repo URL
    gitops_repo_path = Column(String(500))  # Path in repo where manifest was committed

    # Configuration (service-specific parameters)
    configuration = Column(JSONB)  # {namespace: "monitoring", ingress_hostname: "grafana.example.com", ...}

    # Deployment Results
    deployment_log = Column(Text)  # Deployment output/logs
    error_message = Column(Text)  # Error details if failed

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("PropertyEdgeNode")

    __table_args__ = (
        CheckConstraint(
            "deployment_status IN ('pending', 'deploying', 'deployed', 'failed', 'uninstalling', 'uninstalled')",
            name='valid_service_deployment_status'
        ),
        Index('idx_service_deployments_client_id', 'client_id'),
        Index('idx_service_deployments_service_id', 'service_id'),
        Index('idx_service_deployments_status', 'deployment_status'),
        Index('idx_service_deployments_deployed_at', 'deployed_at'),
        UniqueConstraint('client_id', 'service_id', name='uq_client_service'),  # One instance per client
    )


# ============================================================================
# AUDIT LOGGING (EPIC K: RBAC)
# ============================================================================

class AuditLog(Base):
    """
    Audit Log for tracking all critical actions in the system
    EPIC K: RBAC system requires comprehensive audit trail
    """
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # User information
    user_id = Column(String(255), nullable=False)  # Username from Authelia
    user_email = Column(String(255))
    user_role = Column(String(20))  # admin, operator, technician, read_only

    # Action details
    action = Column(String(100), nullable=False)  # created_deployment, updated_hub, deleted_lease, etc.
    resource_type = Column(String(50), nullable=False)  # deployment, hub, work_order, lease, etc.
    resource_id = Column(GUID)  # ID of the resource affected

    # Change tracking (for updates)
    changes = Column(JSONB)  # {"old": {...}, "new": {...}}

    # Request details
    http_method = Column(String(10))  # POST, PUT, PATCH, DELETE, etc.
    endpoint = Column(String(500))  # /api/v1/deployments/123
    ip_address = Column(INET)
    user_agent = Column(String(500))

    # Status
    status_code = Column(Integer)  # HTTP status code (200, 403, 500, etc.)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    duration_ms = Column(Integer)  # Request duration in milliseconds

    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_user_role', 'user_role'),
        Index('idx_audit_logs_success', 'success'),
    )


# ============================================================================
# EDGE NODE COMMANDS (for remote control of hubs)
# ============================================================================

class EdgeNodeCommand(Base):
    """Commands sent from Central Hub to edge hubs for remote device control"""
    __tablename__ = "edge_node_commands"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    hub_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='CASCADE'), nullable=False)

    # Command details
    command_type = Column(String(50), nullable=False)  # service_call, state_change, script, automation
    target_entity = Column(String(255), nullable=False)  # entity_id (e.g., 'light.living_room')
    action = Column(String(100), nullable=False)  # turn_on, turn_off, lock, unlock, trigger, etc.
    parameters = Column(JSONB, default=dict)  # Service parameters (brightness, color, etc.)

    # Command metadata
    created_by = Column(String(255))  # User or system that created command
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Execution tracking
    status = Column(String(20), default='pending')  # pending, executing, success, failed, timeout
    executed_at = Column(DateTime(timezone=True))
    result = Column(JSONB)  # Execution result from hub
    error_message = Column(Text)

    # Timeout (commands older than 5 minutes are considered stale)
    timeout_seconds = Column(Integer, default=300)

    __table_args__ = (
        Index('idx_edge_commands_hub_id', 'hub_id'),
        Index('idx_edge_commands_status', 'status'),
        Index('idx_edge_commands_created_at', 'created_at'),
    )


# ============================================================================
# AI ASSISTANT MODELS (imported from models_ai.py for modularity)
# ============================================================================

from db.models_ai import AIConversation, AIMessage, AITrainingFeedback


# ============================================================================
# HOME ASSISTANT INSTANCE MODELS (imported from models_ha_instance.py for modularity)
# ============================================================================

from db.models_ha_instance import HAInstance, HATerminalSession, HALogAnalysis, HACommandApproval


__all__ = [
    'Property', 'Building', 'Unit', 'Tenant', 'Lease', 'Payment', 'Invoice',
    'WorkOrder', 'WorkOrderTask', 'WorkOrderMaterial', 'WorkOrderEvent', 'Document', 'SmartDevice', 'UtilityMeter', 'UtilityReading',
    'ServicePackage', 'ServiceContract', 'Installation', 'PropertyEdgeNode',
    'Client', 'ComponentSync', 'ServiceDeployment', 'AuditLog', 'Contractor',
    'EdgeNodeCommand',
    'AIConversation', 'AIMessage', 'AITrainingFeedback',
    'HAInstance', 'HATerminalSession', 'HALogAnalysis', 'HACommandApproval'
]
