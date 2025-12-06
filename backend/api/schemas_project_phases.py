"""
Somni Property Manager - Project Phase Schemas
Pydantic models for phased project planning API
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# ============================================================================
# PROJECT PHASE SCHEMAS
# ============================================================================

class ProjectPhaseBase(BaseModel):
    phase_name: str = Field(..., max_length=100)
    phase_letter: str = Field(..., max_length=5)
    phase_number: int = Field(..., ge=1)

    description: str
    deliverables: List[str]  # List of what's included

    # Pricing
    phase_cost: Decimal = Field(..., ge=0)
    deposit_required: Decimal = Field(..., ge=0)
    deposit_percentage: Decimal = Field(default=50.00, ge=0, le=100)

    hardware_cost: Decimal = Field(default=0, ge=0)
    installation_cost: Decimal = Field(default=0, ge=0)
    monthly_service_cost: Decimal = Field(default=0, ge=0)

    # Timeline
    estimated_duration_days: Optional[int] = Field(None, ge=0)
    estimated_start_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None

    # Dependencies
    depends_on_phase_id: Optional[UUID] = None
    can_start_after_days: int = Field(default=0, ge=0)

    # Priority
    is_required: bool = True
    is_milestone: bool = False
    priority_level: int = Field(default=5, ge=1, le=10)

    # Payment terms
    payment_terms: Optional[str] = Field(None, max_length=100)

    # Notes
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None


class ProjectPhaseCreate(ProjectPhaseBase):
    quote_id: UUID


class ProjectPhaseUpdate(BaseModel):
    phase_name: Optional[str] = Field(None, max_length=100)
    phase_letter: Optional[str] = Field(None, max_length=5)
    phase_number: Optional[int] = Field(None, ge=1)

    description: Optional[str] = None
    deliverables: Optional[List[str]] = None

    phase_cost: Optional[Decimal] = Field(None, ge=0)
    deposit_required: Optional[Decimal] = Field(None, ge=0)
    deposit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)

    hardware_cost: Optional[Decimal] = Field(None, ge=0)
    installation_cost: Optional[Decimal] = Field(None, ge=0)
    monthly_service_cost: Optional[Decimal] = Field(None, ge=0)

    estimated_duration_days: Optional[int] = Field(None, ge=0)
    estimated_start_date: Optional[datetime] = None
    estimated_completion_date: Optional[datetime] = None

    actual_start_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    depends_on_phase_id: Optional[UUID] = None
    can_start_after_days: Optional[int] = Field(None, ge=0)

    status: Optional[str] = Field(None, pattern="^(planned|unlocked|in_progress|completed|on_hold|cancelled)$")

    is_required: Optional[bool] = None
    is_milestone: Optional[bool] = None
    priority_level: Optional[int] = Field(None, ge=1, le=10)

    payment_terms: Optional[str] = Field(None, max_length=100)
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None


class ProjectPhase(ProjectPhaseBase):
    id: UUID
    quote_id: UUID

    # Status
    status: str
    deposit_paid: bool
    deposit_paid_at: Optional[datetime] = None
    deposit_amount_paid: Decimal

    # Financial tracking
    total_paid: Decimal
    balance_remaining: Optional[Decimal] = None

    # Actual timeline
    actual_start_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    # Metadata
    created_at: datetime
    updated_at: datetime

    # Nested relationships (optional, can be loaded separately)
    line_items: List['ProjectPhaseLineItem'] = []
    milestones: List['ProjectPhaseMilestone'] = []
    deposits: List['ProjectDeposit'] = []

    class Config:
        from_attributes = True


# ============================================================================
# PROJECT PHASE LINE ITEM SCHEMAS
# ============================================================================

class ProjectPhaseLineItemBase(BaseModel):
    line_number: int = Field(..., ge=1)
    category: Optional[str] = Field(None, max_length=100)
    item_name: str = Field(..., max_length=255)
    description: Optional[str] = None

    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    subtotal: Decimal = Field(..., ge=0)

    item_type: Optional[str] = Field(None, max_length=50)
    recurring: bool = False
    recurring_interval: Optional[str] = Field(None, max_length=20)

    vendor_pricing_id: Optional[UUID] = None
    product_sku: Optional[str] = Field(None, max_length=100)
    product_tier: Optional[str] = Field(None, max_length=50)

    notes: Optional[str] = None


class ProjectPhaseLineItemCreate(ProjectPhaseLineItemBase):
    phase_id: UUID


class ProjectPhaseLineItemUpdate(BaseModel):
    line_number: Optional[int] = Field(None, ge=1)
    category: Optional[str] = Field(None, max_length=100)
    item_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None

    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    subtotal: Optional[Decimal] = Field(None, ge=0)

    item_type: Optional[str] = Field(None, max_length=50)
    recurring: Optional[bool] = None
    recurring_interval: Optional[str] = Field(None, max_length=20)

    status: Optional[str] = Field(None, pattern="^(pending|ordered|delivered|installed|completed|cancelled)$")

    ordered_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    installed_at: Optional[datetime] = None

    vendor_pricing_id: Optional[UUID] = None
    product_sku: Optional[str] = Field(None, max_length=100)
    product_tier: Optional[str] = Field(None, max_length=50)

    notes: Optional[str] = None


class ProjectPhaseLineItem(ProjectPhaseLineItemBase):
    id: UUID
    phase_id: UUID

    status: str
    ordered_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    installed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PROJECT PHASE MILESTONE SCHEMAS
# ============================================================================

class ProjectPhaseMilestoneBase(BaseModel):
    milestone_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    milestone_order: int = Field(..., ge=1)

    target_date: Optional[datetime] = None

    requires_customer_approval: bool = False

    notes: Optional[str] = None


class ProjectPhaseMilestoneCreate(ProjectPhaseMilestoneBase):
    phase_id: UUID


class ProjectPhaseMilestoneUpdate(BaseModel):
    milestone_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    milestone_order: Optional[int] = Field(None, ge=1)

    target_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|blocked|skipped)$")
    completed: Optional[bool] = None
    completed_by: Optional[str] = Field(None, max_length=255)

    requires_customer_approval: Optional[bool] = None
    customer_approved: Optional[bool] = None
    customer_approved_at: Optional[datetime] = None

    blocked_reason: Optional[str] = None
    blocked_at: Optional[datetime] = None

    notes: Optional[str] = None
    completion_notes: Optional[str] = None


class ProjectPhaseMilestone(ProjectPhaseMilestoneBase):
    id: UUID
    phase_id: UUID

    actual_completion_date: Optional[datetime] = None

    status: str
    completed: bool
    completed_by: Optional[str] = None

    customer_approved: bool
    customer_approved_at: Optional[datetime] = None

    blocked_reason: Optional[str] = None
    blocked_at: Optional[datetime] = None

    completion_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PROJECT DEPOSIT SCHEMAS
# ============================================================================

class ProjectDepositBase(BaseModel):
    deposit_amount: Decimal = Field(..., gt=0)

    payment_method: Optional[str] = Field(None, max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=255)

    unlocks_phase: bool = True

    allocated_amount: Optional[Decimal] = Field(None, ge=0)
    allocation_notes: Optional[str] = None

    receipt_number: Optional[str] = Field(None, max_length=50)
    receipt_url: Optional[str] = Field(None, max_length=500)

    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class ProjectDepositCreate(ProjectDepositBase):
    quote_id: UUID
    phase_id: Optional[UUID] = None


class ProjectDepositUpdate(BaseModel):
    deposit_amount: Optional[Decimal] = Field(None, gt=0)

    payment_method: Optional[str] = Field(None, max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=255)
    payment_status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed|refunded)$")

    cleared_date: Optional[datetime] = None

    unlocks_phase: Optional[bool] = None
    phase_unlocked_at: Optional[datetime] = None

    allocated_amount: Optional[Decimal] = Field(None, ge=0)
    allocation_notes: Optional[str] = None

    receipt_number: Optional[str] = Field(None, max_length=50)
    receipt_url: Optional[str] = Field(None, max_length=500)

    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class ProjectDeposit(ProjectDepositBase):
    id: UUID
    quote_id: UUID
    phase_id: Optional[UUID] = None

    deposit_number: str
    payment_status: str

    deposit_date: datetime
    cleared_date: Optional[datetime] = None

    phase_unlocked_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PROJECT TIMELINE SCHEMAS
# ============================================================================

class ProjectTimelineBase(BaseModel):
    project_name: str = Field(..., max_length=255)
    project_description: Optional[str] = None

    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None

    total_estimated_days: Optional[int] = Field(None, ge=0)

    total_project_value: Decimal = Field(..., gt=0)
    total_deposits_required: Optional[Decimal] = Field(None, ge=0)

    project_manager: Optional[str] = Field(None, max_length=255)
    lead_technician: Optional[str] = Field(None, max_length=255)
    assigned_team: Optional[List[str]] = None

    customer_contact_name: Optional[str] = Field(None, max_length=255)
    customer_contact_email: Optional[EmailStr] = None
    customer_contact_phone: Optional[str] = Field(None, max_length=20)

    notes: Optional[str] = None
    customer_notes: Optional[str] = None


class ProjectTimelineCreate(ProjectTimelineBase):
    quote_id: UUID


class ProjectTimelineUpdate(BaseModel):
    project_name: Optional[str] = Field(None, max_length=255)
    project_description: Optional[str] = None

    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    total_estimated_days: Optional[int] = Field(None, ge=0)
    total_actual_days: Optional[int] = Field(None, ge=0)

    status: Optional[str] = Field(None, pattern="^(planning|awaiting_deposit|in_progress|completed|on_hold|cancelled)$")
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)

    total_deposits_received: Optional[Decimal] = Field(None, ge=0)
    total_paid: Optional[Decimal] = Field(None, ge=0)
    balance_remaining: Optional[Decimal] = None

    total_phases: Optional[int] = Field(None, ge=0)
    phases_unlocked: Optional[int] = Field(None, ge=0)
    phases_completed: Optional[int] = Field(None, ge=0)

    project_manager: Optional[str] = Field(None, max_length=255)
    lead_technician: Optional[str] = Field(None, max_length=255)
    assigned_team: Optional[List[str]] = None

    customer_contact_name: Optional[str] = Field(None, max_length=255)
    customer_contact_email: Optional[EmailStr] = None
    customer_contact_phone: Optional[str] = Field(None, max_length=20)

    notes: Optional[str] = None
    customer_notes: Optional[str] = None


class ProjectTimeline(ProjectTimelineBase):
    id: UUID
    quote_id: UUID

    actual_start_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    total_actual_days: Optional[int] = None

    status: str
    completion_percentage: int

    total_deposits_received: Decimal
    total_paid: Decimal
    balance_remaining: Optional[Decimal] = None

    total_phases: int
    phases_unlocked: int
    phases_completed: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SPECIALIZED REQUEST/RESPONSE SCHEMAS
# ============================================================================

class PhaseGenerationRequest(BaseModel):
    """
    Request to auto-generate project phases from a quote
    """
    quote_id: UUID
    number_of_phases: int = Field(..., ge=1, le=10)
    phase_strategy: str = Field(default='even')  # even | priority_based | custom

    # Distribution strategy
    deposit_percentage_per_phase: Decimal = Field(default=50.00, ge=0, le=100)
    include_timeline: bool = True
    average_days_per_phase: Optional[int] = Field(None, ge=1)


class PhaseGenerationResponse(BaseModel):
    """
    Response after generating phases
    """
    quote_id: UUID
    phases_created: int
    total_project_value: Decimal
    total_deposits_required: Decimal
    estimated_total_duration_days: Optional[int] = None

    phases: List[ProjectPhase]
    timeline: Optional[ProjectTimeline] = None


class DepositApplicationRequest(BaseModel):
    """
    Apply a deposit to unlock a phase
    """
    quote_id: UUID
    phase_id: UUID
    deposit_amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=255)


class DepositApplicationResponse(BaseModel):
    """
    Response after applying deposit
    """
    deposit_id: UUID
    deposit_number: str
    phase_unlocked: bool
    phase_id: UUID
    phase_name: str
    amount_applied: Decimal
    balance_remaining: Decimal
    next_phase_id: Optional[UUID] = None
    next_phase_deposit_required: Optional[Decimal] = None


class ProjectPhaseProgressSummary(BaseModel):
    """
    Summary of project progress across all phases
    """
    quote_id: UUID
    project_name: str

    # Financial summary
    total_project_value: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    payment_percentage: Decimal

    # Phase summary
    total_phases: int
    phases_planned: int
    phases_unlocked: int
    phases_in_progress: int
    phases_completed: int

    # Timeline summary
    project_status: str
    completion_percentage: int
    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    estimated_days_remaining: Optional[int] = None

    # Next steps
    next_deposit_required: Optional[Decimal] = None
    next_phase_name: Optional[str] = None

    # Phases detail
    phases: List[ProjectPhase]


class ProjectFinancialReport(BaseModel):
    """
    Financial report for a phased project
    """
    quote_id: UUID
    quote_number: str

    # Total values
    total_project_value: Decimal
    total_hardware_cost: Decimal
    total_installation_cost: Decimal
    total_monthly_service_cost: Decimal

    # Payment tracking
    total_deposits_required: Decimal
    total_deposits_received: Decimal
    total_paid: Decimal
    balance_remaining: Decimal

    # Payment breakdown by phase
    phase_payments: List[Dict[str, Any]]

    # Deposit history
    deposits: List[ProjectDeposit]

    # Summary
    all_deposits_received: bool
    project_fully_paid: bool
    outstanding_balance: Decimal


# Update forward references
ProjectPhase.model_rebuild()
