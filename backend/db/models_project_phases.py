"""
Somni Property Manager - Project Phase Models
Database models for phased project planning with incremental deposits

Enables large smart home/building projects to be broken into phases (A, B, C, etc.)
where each deposit unlocks specific deliverables and timelines.
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


class ProjectPhase(Base):
    """
    Phases within a project - allows breaking large projects into incremental stages

    Example:
    - Phase A (Foundation): $15K - Core infrastructure, basic smart locks, 1 thermostat
    - Phase B (Enhancement): $25K - Full HVAC automation, advanced lighting
    - Phase C (Premium): $40K - Security cameras, access control, energy monitoring
    """
    __tablename__ = "project_phases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)

    # Phase identification
    phase_name = Column(String(100), nullable=False)  # "Phase A: Foundation", "Phase B: Enhancement"
    phase_letter = Column(String(5), nullable=False)  # A, B, C, etc.
    phase_number = Column(Integer, nullable=False)  # 1, 2, 3 for ordering

    # Phase description
    description = Column(Text, nullable=False)
    deliverables = Column(JSON, nullable=False)  # List of what's included in this phase

    # Pricing
    phase_cost = Column(Numeric(12, 2), nullable=False)  # Total cost of this phase
    deposit_required = Column(Numeric(12, 2), nullable=False)  # Deposit to unlock this phase
    deposit_percentage = Column(Numeric(5, 2), default=50.00)  # % of phase cost required as deposit

    # Hardware breakdown (one-time costs)
    hardware_cost = Column(Numeric(12, 2), default=0)
    installation_cost = Column(Numeric(12, 2), default=0)

    # Recurring costs (monthly)
    monthly_service_cost = Column(Numeric(10, 2), default=0)

    # Timeline
    estimated_duration_days = Column(Integer)  # How long this phase takes
    estimated_start_date = Column(DateTime(timezone=True))
    estimated_completion_date = Column(DateTime(timezone=True))

    # Actual timeline (once started)
    actual_start_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))

    # Dependencies
    depends_on_phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='SET NULL'))
    can_start_after_days = Column(Integer, default=0)  # Days after dependency completion

    # Status tracking
    status = Column(String(50), default='planned')  # planned | unlocked | in_progress | completed | on_hold | cancelled
    deposit_paid = Column(Boolean, default=False)
    deposit_paid_at = Column(DateTime(timezone=True))
    deposit_amount_paid = Column(Numeric(12, 2), default=0)

    # Payment tracking
    total_paid = Column(Numeric(12, 2), default=0)
    balance_remaining = Column(Numeric(12, 2))
    payment_terms = Column(String(100))  # "50% deposit, 50% on completion"

    # Priority and grouping
    is_required = Column(Boolean, default=True)  # Required vs. optional phase
    is_milestone = Column(Boolean, default=False)  # Major milestone phase
    priority_level = Column(Integer, default=5)  # 1-10, for sorting optional phases

    # ========================================================================
    # CONTRACTOR INTEGRATION
    # ========================================================================
    # Assigned contractor for this phase
    assigned_contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='SET NULL'))
    contractor_status = Column(String(50), default='not_assigned')  # not_assigned | bidding | assigned | in_progress | completed
    contractor_assigned_at = Column(DateTime(timezone=True))
    contractor_started_at = Column(DateTime(timezone=True))
    contractor_completed_at = Column(DateTime(timezone=True))

    # Contractor payment tracking
    contractor_quote_amount = Column(Numeric(12, 2))  # Contractor's quote for this phase
    contractor_paid_amount = Column(Numeric(12, 2), default=0)  # Amount paid to contractor
    contractor_balance = Column(Numeric(12, 2))  # Remaining payment owed to contractor

    # Performance tracking
    contractor_rating = Column(Numeric(3, 2))  # 1.00 - 5.00 rating after completion
    contractor_review = Column(Text)  # Review/feedback on contractor performance
    contractor_on_time = Column(Boolean)  # Did contractor finish on time?

    # Notes
    internal_notes = Column(Text)  # Internal planning notes
    customer_notes = Column(Text)  # Notes visible to customer

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="project_phases")
    assigned_contractor = relationship("Contractor", foreign_keys=[assigned_contractor_id])
    line_items = relationship("ProjectPhaseLineItem", back_populates="phase", cascade="all, delete-orphan")
    milestones = relationship("ProjectPhaseMilestone", back_populates="phase", cascade="all, delete-orphan")
    deposits = relationship("ProjectDeposit", back_populates="phase", cascade="all, delete-orphan")
    dependencies = relationship("ProjectPhase", remote_side=[id], backref="dependent_phases")
    contractor_bids = relationship("ContractorBid", back_populates="phase", cascade="all, delete-orphan")
    contractor_payments = relationship("ContractorPayment", back_populates="phase", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'unlocked', 'in_progress', 'completed', 'on_hold', 'cancelled')",
            name='valid_project_phase_status'
        ),
        CheckConstraint(
            "contractor_status IN ('not_assigned', 'bidding', 'assigned', 'in_progress', 'completed')",
            name='valid_contractor_status'
        ),
        CheckConstraint(
            "deposit_percentage >= 0 AND deposit_percentage <= 100",
            name='valid_deposit_percentage'
        ),
        Index('idx_project_phases_quote_id', 'quote_id'),
        Index('idx_project_phases_status', 'status'),
        Index('idx_project_phases_phase_number', 'phase_number'),
        Index('idx_project_phases_depends_on', 'depends_on_phase_id'),
        Index('idx_project_phases_contractor_id', 'assigned_contractor_id'),
        Index('idx_project_phases_contractor_status', 'contractor_status'),
    )


class ProjectPhaseLineItem(Base):
    """
    Individual line items within a project phase
    Links specific hardware, services, or labor to phases
    """
    __tablename__ = "project_phase_line_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False)

    # Line item details
    line_number = Column(Integer, nullable=False)
    category = Column(String(100))  # Hardware, Installation, Service, Automation, Integration
    item_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Pricing
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    # Item type
    item_type = Column(String(50))  # hardware | installation | service | subscription
    recurring = Column(Boolean, default=False)  # True if monthly/annual cost
    recurring_interval = Column(String(20))  # monthly, annual

    # Product details
    vendor_pricing_id = Column(GUID, ForeignKey('vendor_pricing.id', ondelete='SET NULL'))
    product_sku = Column(String(100))
    product_tier = Column(String(50))  # economy, standard, premium

    # Status
    status = Column(String(50), default='pending')  # pending | ordered | delivered | installed | completed
    ordered_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    installed_at = Column(DateTime(timezone=True))

    # Notes
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    phase = relationship("ProjectPhase", back_populates="line_items")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'ordered', 'delivered', 'installed', 'completed', 'cancelled')",
            name='valid_phase_line_item_status'
        ),
        Index('idx_project_phase_line_items_phase_id', 'phase_id'),
        Index('idx_project_phase_line_items_status', 'status'),
    )


class ProjectPhaseMilestone(Base):
    """
    Milestones within a project phase
    Tracks specific deliverables and completion checkpoints
    """
    __tablename__ = "project_phase_milestones"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False)

    # Milestone details
    milestone_name = Column(String(255), nullable=False)
    description = Column(Text)
    milestone_order = Column(Integer, nullable=False)  # Order within phase

    # Timeline
    target_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))

    # Status
    status = Column(String(50), default='pending')  # pending | in_progress | completed | blocked | skipped
    completed = Column(Boolean, default=False)
    completed_by = Column(String(255))

    # Approval
    requires_customer_approval = Column(Boolean, default=False)
    customer_approved = Column(Boolean, default=False)
    customer_approved_at = Column(DateTime(timezone=True))

    # Blocking issues
    blocked_reason = Column(Text)
    blocked_at = Column(DateTime(timezone=True))

    # Notes
    notes = Column(Text)
    completion_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    phase = relationship("ProjectPhase", back_populates="milestones")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'blocked', 'skipped')",
            name='valid_milestone_status'
        ),
        Index('idx_project_phase_milestones_phase_id', 'phase_id'),
        Index('idx_project_phase_milestones_status', 'status'),
        Index('idx_project_phase_milestones_order', 'milestone_order'),
    )


class ProjectDeposit(Base):
    """
    Deposits made toward project phases
    Tracks payments that unlock phases
    """
    __tablename__ = "project_deposits"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False)
    phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='SET NULL'))

    # Deposit details
    deposit_number = Column(String(50), nullable=False, unique=True)  # DEP-2026-001
    deposit_amount = Column(Numeric(12, 2), nullable=False)

    # Payment info
    payment_method = Column(String(50))  # credit_card, ach, check, wire, cash
    payment_reference = Column(String(255))  # Transaction ID, check number, etc.
    payment_status = Column(String(50), default='pending')  # pending | processing | completed | failed | refunded

    # Dates
    deposit_date = Column(DateTime(timezone=True), server_default=func.now())
    cleared_date = Column(DateTime(timezone=True))

    # Phase unlocking
    unlocks_phase = Column(Boolean, default=True)  # Does this deposit unlock the phase?
    phase_unlocked_at = Column(DateTime(timezone=True))

    # Allocation (if deposit applies to multiple phases)
    allocated_amount = Column(Numeric(12, 2))
    allocation_notes = Column(Text)

    # Receipt and documentation
    receipt_number = Column(String(50))
    receipt_url = Column(String(500))  # URL to receipt/invoice

    # Notes
    notes = Column(Text)
    internal_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="deposits")
    phase = relationship("ProjectPhase", back_populates="deposits")

    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')",
            name='valid_deposit_payment_status'
        ),
        Index('idx_project_deposits_quote_id', 'quote_id'),
        Index('idx_project_deposits_phase_id', 'phase_id'),
        Index('idx_project_deposits_payment_status', 'payment_status'),
        Index('idx_project_deposits_number', 'deposit_number'),
    )


class ProjectTimeline(Base):
    """
    Overall project timeline and scheduling
    Provides high-level view of project from start to finish
    """
    __tablename__ = "project_timelines"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quote_id = Column(GUID, ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Timeline details
    project_name = Column(String(255), nullable=False)
    project_description = Column(Text)

    # Overall timeline
    planned_start_date = Column(DateTime(timezone=True))
    planned_completion_date = Column(DateTime(timezone=True))
    actual_start_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))

    # Duration estimates
    total_estimated_days = Column(Integer)
    total_actual_days = Column(Integer)

    # Status
    status = Column(String(50), default='planning')  # planning | awaiting_deposit | in_progress | completed | on_hold | cancelled
    completion_percentage = Column(Integer, default=0)  # 0-100

    # Financial summary
    total_project_value = Column(Numeric(12, 2), nullable=False)
    total_deposits_required = Column(Numeric(12, 2))
    total_deposits_received = Column(Numeric(12, 2), default=0)
    total_paid = Column(Numeric(12, 2), default=0)
    balance_remaining = Column(Numeric(12, 2))

    # Phase summary
    total_phases = Column(Integer, default=0)
    phases_unlocked = Column(Integer, default=0)
    phases_completed = Column(Integer, default=0)

    # Team assignment
    project_manager = Column(String(255))
    lead_technician = Column(String(255))
    assigned_team = Column(JSON)  # List of team members

    # Customer relationship
    customer_contact_name = Column(String(255))
    customer_contact_email = Column(String(255))
    customer_contact_phone = Column(String(20))

    # Notes
    notes = Column(Text)
    customer_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quote = relationship("Quote", back_populates="project_timeline", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('planning', 'awaiting_deposit', 'in_progress', 'completed', 'on_hold', 'cancelled')",
            name='valid_project_timeline_status'
        ),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name='valid_completion_percentage'
        ),
        Index('idx_project_timelines_quote_id', 'quote_id'),
        Index('idx_project_timelines_status', 'status'),
    )


class ContractorBid(Base):
    """
    Contractor bids on project phases

    Enables competitive bidding where multiple contractors can bid on a phase.
    Customer or project manager selects winning bid.
    """
    __tablename__ = "contractor_bids"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False)
    contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='CASCADE'), nullable=False)

    # Bid details
    bid_amount = Column(Numeric(12, 2), nullable=False)
    bid_currency = Column(String(3), default='USD')

    # Timeline bid
    estimated_start_date = Column(DateTime(timezone=True))
    estimated_completion_date = Column(DateTime(timezone=True))
    estimated_duration_days = Column(Integer)

    # Bid breakdown
    labor_cost = Column(Numeric(12, 2))
    material_cost = Column(Numeric(12, 2))
    equipment_cost = Column(Numeric(12, 2))
    other_costs = Column(Numeric(12, 2))

    # Bid details
    scope_of_work = Column(Text)  # Contractor's understanding of work
    exclusions = Column(Text)  # What's not included
    assumptions = Column(Text)  # Assumptions made
    notes = Column(Text)

    # Payment terms proposed by contractor
    payment_schedule = Column(String(100))  # "50% upfront, 50% on completion"
    warranty_period_days = Column(Integer)  # Warranty offered
    warranty_terms = Column(Text)

    # Status tracking
    status = Column(String(50), default='submitted')  # submitted | under_review | accepted | rejected | withdrawn
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))
    accepted_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))

    # Selection
    is_selected = Column(Boolean, default=False)
    selected_by = Column(String(255))  # User who selected this bid
    rejection_reason = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    phase = relationship("ProjectPhase", back_populates="contractor_bids")
    contractor = relationship("Contractor")

    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted', 'under_review', 'accepted', 'rejected', 'withdrawn')",
            name='valid_contractor_bid_status'
        ),
        Index('idx_contractor_bids_phase_id', 'phase_id'),
        Index('idx_contractor_bids_contractor_id', 'contractor_id'),
        Index('idx_contractor_bids_status', 'status'),
        Index('idx_contractor_bids_is_selected', 'is_selected'),
    )


class ContractorPayment(Base):
    """
    Payments made to contractors for project phase work

    Tracks payments to contractors separate from customer deposits.
    Ensures proper accounting of cash flow: deposits received vs. contractor payments made.
    """
    __tablename__ = "contractor_payments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    phase_id = Column(GUID, ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False)
    contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='CASCADE'), nullable=False)

    # Payment details
    payment_number = Column(String(50), nullable=False, unique=True)  # CPY-2026-001
    payment_amount = Column(Numeric(12, 2), nullable=False)
    payment_type = Column(String(50), default='progress')  # deposit | progress | final | bonus | retention

    # Payment method
    payment_method = Column(String(50))  # check | ach | wire | credit_card | cash
    payment_reference = Column(String(255))  # Check number, transaction ID, etc.

    # Invoice tracking
    invoice_number = Column(String(100))
    invoice_date = Column(DateTime(timezone=True))
    invoice_amount = Column(Numeric(12, 2))
    invoice_url = Column(String(500))  # Link to invoice PDF

    # Status
    status = Column(String(50), default='pending')  # pending | scheduled | paid | failed | cancelled
    scheduled_date = Column(DateTime(timezone=True))  # When payment is scheduled
    paid_date = Column(DateTime(timezone=True))  # Actual payment date
    cleared_date = Column(DateTime(timezone=True))  # When funds cleared

    # Milestone tracking
    milestone_id = Column(GUID, ForeignKey('project_phase_milestones.id', ondelete='SET NULL'))
    milestone_completion_verified = Column(Boolean, default=False)  # Did contractor complete work?

    # Retention (holdback)
    is_retention = Column(Boolean, default=False)  # Is this a retention payment?
    retention_percentage = Column(Numeric(5, 2))  # e.g., 10.00 for 10% retention
    retention_release_date = Column(DateTime(timezone=True))

    # Notes
    notes = Column(Text)
    internal_notes = Column(Text)

    # Approval workflow
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    phase = relationship("ProjectPhase", back_populates="contractor_payments")
    contractor = relationship("Contractor")
    milestone = relationship("ProjectPhaseMilestone")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'scheduled', 'paid', 'failed', 'cancelled')",
            name='valid_contractor_payment_status'
        ),
        CheckConstraint(
            "payment_type IN ('deposit', 'progress', 'final', 'bonus', 'retention')",
            name='valid_payment_type'
        ),
        Index('idx_contractor_payments_phase_id', 'phase_id'),
        Index('idx_contractor_payments_contractor_id', 'contractor_id'),
        Index('idx_contractor_payments_status', 'status'),
        Index('idx_contractor_payments_payment_number', 'payment_number'),
        Index('idx_contractor_payments_paid_date', 'paid_date'),
    )
