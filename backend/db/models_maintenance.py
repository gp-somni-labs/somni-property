"""
Maintenance Scheduling Models
Tracks preventive and recurring maintenance for buildings
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
import enum

from db.models import Base


class MaintenanceFrequency(str, enum.Enum):
    """Frequency of maintenance"""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class MaintenancePriority(str, enum.Enum):
    """Priority level for maintenance"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenanceCategory(str, enum.Enum):
    """Category of maintenance work"""
    HVAC = "hvac"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    STRUCTURAL = "structural"
    ROOFING = "roofing"
    LANDSCAPING = "landscaping"
    CLEANING = "cleaning"
    FIRE_SAFETY = "fire_safety"
    SECURITY = "security"
    ELEVATORS = "elevators"
    PAINTING = "painting"
    POOL = "pool"
    PEST_CONTROL = "pest_control"
    APPLIANCES = "appliances"
    OTHER = "other"


class MaintenanceScheduleStatus(str, enum.Enum):
    """Status of maintenance schedule"""
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class MaintenanceTaskStatus(str, enum.Enum):
    """Status of individual maintenance task"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class MaintenanceSchedule(Base):
    """
    Recurring maintenance schedule for buildings

    Examples:
    - HVAC filter replacement every 3 months
    - Fire alarm testing annually
    - Pool cleaning weekly
    - Landscape maintenance biweekly
    """
    __tablename__ = "maintenance_schedules"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Relationships
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=True)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)

    # Schedule Details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="other")
    priority = Column(String(20), nullable=False, default="medium")

    # Frequency Configuration
    frequency = Column(String(20), nullable=False)
    interval_days = Column(Integer, nullable=True)  # For custom frequency

    # Scheduling
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)  # Optional end date
    next_due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    last_completed_date = Column(DateTime(timezone=True), nullable=True)

    # Task Configuration
    estimated_duration_hours = Column(DECIMAL(5, 2), nullable=True)  # How long it takes
    estimated_cost = Column(DECIMAL(10, 2), nullable=True)

    # Instructions
    instructions = Column(Text, nullable=True)
    checklist = Column(JSONB, nullable=True)  # JSON array of checklist items
    required_tools = Column(ARRAY(String), nullable=True)
    required_materials = Column(ARRAY(String), nullable=True)

    # Auto-creation settings
    auto_create_workorder = Column(Boolean, default=True)  # Auto-create work order when due
    auto_assign_contractor = Column(Boolean, default=False)  # Auto-assign to contractor
    advance_notice_days = Column(Integer, default=7)  # Create task N days in advance

    # Status
    status = Column(String(20), nullable=False, default="active")
    is_active = Column(Boolean, default=True, index=True)

    # Metadata
    notes = Column(Text, nullable=True)
    attachments = Column(JSONB, nullable=True)  # URLs to manuals, photos, etc.
    tags = Column(ARRAY(String), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    # Relationships
    property = relationship("Property", back_populates="maintenance_schedules")
    building = relationship("Building", back_populates="maintenance_schedules")
    unit = relationship("Unit", back_populates="maintenance_schedules")
    contractor = relationship("Contractor", back_populates="maintenance_schedules")
    tasks = relationship("MaintenanceTask", back_populates="schedule", cascade="all, delete-orphan")


class MaintenanceTask(Base):
    """
    Individual instance of maintenance work
    Created from schedules or ad-hoc
    """
    __tablename__ = "maintenance_tasks"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Relationships
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_schedules.id", ondelete="SET NULL"), nullable=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=True)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)

    # Task Details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="other")
    priority = Column(String(20), nullable=False, default="medium")

    # Scheduling
    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Execution Details
    estimated_duration_hours = Column(DECIMAL(5, 2), nullable=True)
    actual_duration_hours = Column(DECIMAL(5, 2), nullable=True)
    estimated_cost = Column(DECIMAL(10, 2), nullable=True)
    actual_cost = Column(DECIMAL(10, 2), nullable=True)

    # Instructions & Completion
    instructions = Column(Text, nullable=True)
    checklist = Column(JSONB, nullable=True)  # JSON array with completion status
    completion_notes = Column(Text, nullable=True)
    completion_photos = Column(JSONB, nullable=True)  # Array of photo URLs

    # Status
    status = Column(String(20), nullable=False, default="scheduled", index=True)
    is_overdue = Column(Boolean, default=False, index=True)

    # Metadata
    assigned_to = Column(String(255), nullable=True)  # Staff member
    completed_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    schedule = relationship("MaintenanceSchedule", back_populates="tasks")
    property = relationship("Property", back_populates="maintenance_tasks")
    building = relationship("Building", back_populates="maintenance_tasks")
    unit = relationship("Unit", back_populates="maintenance_tasks")
    contractor = relationship("Contractor", back_populates="maintenance_tasks")
    work_order = relationship("WorkOrder", back_populates="maintenance_task")


# Add reverse relationships to existing models
# These would be added to the existing Property, Building, Unit, Contractor, WorkOrder models:

"""
In db/models.py, add these relationships:

class Property(Base):
    ...
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="property")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="property")

class Building(Base):
    ...
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="building")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="building")

class Unit(Base):
    ...
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="unit")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="unit")

class Contractor(Base):
    ...
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="contractor")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="contractor")

class WorkOrder(Base):
    ...
    maintenance_task = relationship("MaintenanceTask", back_populates="work_order", uselist=False)
"""
