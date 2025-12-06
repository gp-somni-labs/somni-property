"""
Pydantic schemas for Maintenance Scheduling API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class MaintenanceFrequency(str, Enum):
    """Frequency of maintenance"""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class MaintenancePriority(str, Enum):
    """Priority level for maintenance"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenanceCategory(str, Enum):
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


class MaintenanceScheduleStatus(str, Enum):
    """Status of maintenance schedule"""
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class MaintenanceTaskStatus(str, Enum):
    """Status of individual maintenance task"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


# ============================================================================
# MAINTENANCE SCHEDULE SCHEMAS
# ============================================================================

class MaintenanceScheduleBase(BaseModel):
    """Base schema for maintenance schedule"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: MaintenanceCategory
    priority: MaintenancePriority = MaintenancePriority.MEDIUM

    # Location (at least one required)
    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None

    # Contractor
    contractor_id: Optional[UUID] = None

    # Frequency
    frequency: MaintenanceFrequency
    interval_days: Optional[int] = Field(None, ge=1, le=365)

    # Dates
    start_date: datetime
    end_date: Optional[datetime] = None

    # Task configuration
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999.99)
    estimated_cost: Optional[Decimal] = Field(None, ge=0, le=99999999.99)

    # Instructions
    instructions: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    required_tools: Optional[List[str]] = None
    required_materials: Optional[List[str]] = None

    # Auto-creation settings
    auto_create_workorder: bool = True
    auto_assign_contractor: bool = False
    advance_notice_days: int = Field(7, ge=0, le=365)

    # Metadata
    notes: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None

    @field_validator('interval_days')
    @classmethod
    def validate_interval_days(cls, v, info):
        """Validate interval_days is provided for custom frequency"""
        if info.data.get('frequency') == MaintenanceFrequency.CUSTOM and v is None:
            raise ValueError('interval_days is required for custom frequency')
        return v


class MaintenanceScheduleCreate(MaintenanceScheduleBase):
    """Schema for creating maintenance schedule"""
    pass


class MaintenanceScheduleUpdate(BaseModel):
    """Schema for updating maintenance schedule"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[MaintenanceCategory] = None
    priority: Optional[MaintenancePriority] = None

    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    contractor_id: Optional[UUID] = None

    frequency: Optional[MaintenanceFrequency] = None
    interval_days: Optional[int] = Field(None, ge=1, le=365)

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999.99)
    estimated_cost: Optional[Decimal] = Field(None, ge=0, le=99999999.99)

    instructions: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    required_tools: Optional[List[str]] = None
    required_materials: Optional[List[str]] = None

    auto_create_workorder: Optional[bool] = None
    auto_assign_contractor: Optional[bool] = None
    advance_notice_days: Optional[int] = Field(None, ge=0, le=365)

    notes: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    status: Optional[MaintenanceScheduleStatus] = None


class MaintenanceScheduleResponse(MaintenanceScheduleBase):
    """Schema for maintenance schedule response"""
    id: UUID
    status: MaintenanceScheduleStatus
    is_active: bool
    next_due_date: Optional[datetime] = None
    last_completed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    # Task count (will be added by API)
    total_tasks: Optional[int] = 0
    completed_tasks: Optional[int] = 0

    class Config:
        from_attributes = True


# ============================================================================
# MAINTENANCE TASK SCHEMAS
# ============================================================================

class MaintenanceTaskBase(BaseModel):
    """Base schema for maintenance task"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: MaintenanceCategory
    priority: MaintenancePriority = MaintenancePriority.MEDIUM

    # Location (at least one required)
    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None

    # Assignment
    contractor_id: Optional[UUID] = None
    assigned_to: Optional[str] = None

    # Scheduling
    scheduled_date: datetime
    due_date: Optional[datetime] = None

    # Cost estimates
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999.99)
    estimated_cost: Optional[Decimal] = Field(None, ge=0, le=99999999.99)

    # Instructions
    instructions: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None

    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class MaintenanceTaskCreate(MaintenanceTaskBase):
    """Schema for creating maintenance task"""
    schedule_id: Optional[UUID] = None  # Link to parent schedule (optional for ad-hoc)
    work_order_id: Optional[UUID] = None  # Link to existing work order


class MaintenanceTaskUpdate(BaseModel):
    """Schema for updating maintenance task"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[MaintenanceCategory] = None
    priority: Optional[MaintenancePriority] = None

    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None

    contractor_id: Optional[UUID] = None
    assigned_to: Optional[str] = None

    scheduled_date: Optional[datetime] = None
    due_date: Optional[datetime] = None

    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999.99)
    estimated_cost: Optional[Decimal] = Field(None, ge=0, le=99999999.99)

    instructions: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class MaintenanceTaskComplete(BaseModel):
    """Schema for completing maintenance task"""
    completion_notes: Optional[str] = None
    completion_photos: Optional[List[Dict[str, str]]] = None  # List of {"url": "...", "caption": "..."}
    actual_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999.99)
    actual_cost: Optional[Decimal] = Field(None, ge=0, le=99999999.99)
    checklist: Optional[List[Dict[str, Any]]] = None  # Updated checklist with completed items


class MaintenanceTaskResponse(MaintenanceTaskBase):
    """Schema for maintenance task response"""
    id: UUID
    schedule_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None

    status: MaintenanceTaskStatus
    is_overdue: bool

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    actual_duration_hours: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None

    completion_notes: Optional[str] = None
    completion_photos: Optional[List[Dict[str, str]]] = None
    completed_by: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD & REPORTING SCHEMAS
# ============================================================================

class MaintenanceDashboard(BaseModel):
    """Schema for maintenance dashboard statistics"""
    # Upcoming tasks
    upcoming_7_days: int = 0
    upcoming_30_days: int = 0

    # Overdue tasks
    overdue_count: int = 0
    overdue_critical: int = 0

    # This month stats
    completed_this_month: int = 0
    total_cost_this_month: Decimal = Decimal('0.00')

    # Active schedules
    active_schedules: int = 0
    paused_schedules: int = 0

    # By category (top 5)
    tasks_by_category: Dict[str, int] = {}

    # By status
    tasks_by_status: Dict[str, int] = {}


class MaintenanceUpcoming(BaseModel):
    """Schema for upcoming maintenance tasks"""
    tasks: List[MaintenanceTaskResponse]
    total: int


class MaintenanceOverdue(BaseModel):
    """Schema for overdue maintenance tasks"""
    tasks: List[MaintenanceTaskResponse]
    total: int
    total_critical: int


# ============================================================================
# FILTER SCHEMAS
# ============================================================================

class MaintenanceScheduleFilters(BaseModel):
    """Filters for maintenance schedule list"""
    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    contractor_id: Optional[UUID] = None
    category: Optional[MaintenanceCategory] = None
    priority: Optional[MaintenancePriority] = None
    frequency: Optional[MaintenanceFrequency] = None
    status: Optional[MaintenanceScheduleStatus] = None
    is_active: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)


class MaintenanceTaskFilters(BaseModel):
    """Filters for maintenance task list"""
    schedule_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    building_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    contractor_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    category: Optional[MaintenanceCategory] = None
    priority: Optional[MaintenancePriority] = None
    status: Optional[MaintenanceTaskStatus] = None
    is_overdue: Optional[bool] = None
    assigned_to: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
