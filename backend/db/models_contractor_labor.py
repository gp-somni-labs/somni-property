"""
Contractor Labor Documentation Models
Comprehensive tracking of contractor work, photos, notes, time, and materials
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    Text, ForeignKey, JSON, CheckConstraint, Index, Date, Time
)
from sqlalchemy.dialects.postgresql import JSONB
# Note: POINT type requires PostGIS; using JSONB for GPS coordinates instead: {"lat": x, "lng": y}
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID
from db.models import Base


class QuoteLaborItemPhoto(Base):
    """
    Photo documentation for labor tasks
    Before/after photos, progress updates, example work, issues, etc.
    """
    __tablename__ = "quote_labor_item_photos"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Photo metadata
    photo_type = Column(String(50), nullable=False)  # before, after, progress, example, issue, completed, safety, equipment
    file_url = Column(Text, nullable=False)
    file_path = Column(Text)
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # Photo details
    caption = Column(Text)
    description = Column(Text)
    photo_taken_at = Column(DateTime(timezone=True), server_default=func.now())
    photo_taken_by = Column(String(255))
    photographer_type = Column(String(50))  # contractor, staff, customer

    # Location metadata
    gps_coordinates = Column(JSONB)  # {"lat": x, "lng": y}
    location_notes = Column(Text)

    # Categorization
    tags = Column(JSONB, default=list)
    related_task = Column(String(255))

    # Analysis/annotations
    annotations = Column(JSONB, default=list)  # Image annotations/markup
    ai_analysis = Column(JSONB)

    # Display settings
    display_order = Column(Integer, default=0)
    show_to_customer = Column(Boolean, default=True)
    show_in_pdf = Column(Boolean, default=True)
    is_thumbnail = Column(Boolean, default=False)

    # Quality/review
    approved_for_display = Column(Boolean, default=True)
    reviewed_by = Column(String(255))
    reviewed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="photos")

    __table_args__ = (
        Index('idx_labor_photos_item_id', 'labor_item_id'),
        Index('idx_labor_photos_type', 'photo_type'),
        Index('idx_labor_photos_taken_at', 'photo_taken_at'),
        Index('idx_labor_photos_display_order', 'labor_item_id', 'display_order'),
    )


class QuoteLaborItemNote(Base):
    """
    Contractor notes, updates, and communication thread for labor tasks
    Progress updates, issues, material requests, questions, completion notes
    """
    __tablename__ = "quote_labor_item_notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Note content
    note_type = Column(String(50), nullable=False)  # progress_update, issue, material_request, question, completion, customer_feedback
    note_text = Column(Text, nullable=False)
    note_title = Column(String(255))

    # Attribution
    created_by = Column(String(255), nullable=False)
    created_by_type = Column(String(50), nullable=False)  # contractor, staff, customer, system
    created_by_id = Column(GUID)

    # Visibility
    is_internal = Column(Boolean, default=False)
    show_to_customer = Column(Boolean, default=True)
    requires_response = Column(Boolean, default=False)

    # Response/resolution
    responded_to = Column(Boolean, default=False)
    responded_by = Column(String(255))
    responded_at = Column(DateTime(timezone=True))
    response_text = Column(Text)

    # Categorization
    priority = Column(String(20))  # low, normal, high, urgent
    tags = Column(JSONB, default=list)

    # Attachments
    attached_photo_ids = Column(JSONB, default=list)
    attached_files = Column(JSONB, default=list)

    # Time tracking
    hours_worked = Column(Numeric(10, 2))
    work_date = Column(Date)

    # Location
    location_coords = Column(JSONB)  # {"lat": x, "lng": y}
    location_name = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="notes")

    __table_args__ = (
        Index('idx_labor_notes_item_id', 'labor_item_id'),
        Index('idx_labor_notes_type', 'note_type'),
        Index('idx_labor_notes_created_at', 'created_at'),
    )


class QuoteLaborTimeEntry(Base):
    """
    Detailed time tracking for labor tasks
    Clock in/out, duration, breaks, billing, location verification
    """
    __tablename__ = "quote_labor_time_entries"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Time details
    work_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    duration_hours = Column(Numeric(10, 2), nullable=False)

    # Worker info
    contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='SET NULL'))
    worker_name = Column(String(255), nullable=False)
    worker_role = Column(String(100))  # lead_tech, assistant, apprentice

    # Work performed
    work_description = Column(Text)
    tasks_completed = Column(JSONB, default=list)

    # Billing
    hourly_rate = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))
    billable = Column(Boolean, default=True)
    approved = Column(Boolean, default=False)
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))

    # Location verification
    clock_in_location = Column(JSONB)  # {"lat": x, "lng": y}
    clock_out_location = Column(JSONB)  # {"lat": x, "lng": y}
    verified = Column(Boolean, default=False)

    # Break time
    break_duration_hours = Column(Numeric(10, 2), default=0)

    # Notes
    notes = Column(Text)
    issues_encountered = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="time_entries")
    contractor = relationship("Contractor")

    __table_args__ = (
        Index('idx_labor_time_item_id', 'labor_item_id'),
        Index('idx_labor_time_contractor', 'contractor_id'),
        Index('idx_labor_time_date', 'work_date'),
        Index('idx_labor_time_approved', 'approved'),
    )


class QuoteLaborMaterialUsed(Base):
    """
    Actual materials used vs estimated for cost tracking
    Tracks variance and reasons for differences
    """
    __tablename__ = "quote_labor_materials_used"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Material details
    material_name = Column(String(255), nullable=False)
    material_category = Column(String(100))
    quantity_used = Column(Numeric(10, 2), nullable=False)
    unit_type = Column(String(50), nullable=False)

    # Pricing
    unit_cost = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))

    # Vendor/source
    vendor_name = Column(String(255))
    purchase_order_number = Column(String(100))
    receipt_photo_url = Column(Text)

    # Tracking
    used_date = Column(Date)
    recorded_by = Column(String(255))

    # Comparison to estimate
    was_estimated = Column(Boolean, default=False)
    estimated_quantity = Column(Numeric(10, 2))
    quantity_variance = Column(Numeric(10, 2))

    # Notes
    notes = Column(Text)
    reason_for_variance = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="materials_used")

    __table_args__ = (
        Index('idx_labor_materials_item_id', 'labor_item_id'),
        Index('idx_labor_materials_category', 'material_category'),
        Index('idx_labor_materials_date', 'used_date'),
    )


class QuoteLaborItemHistory(Base):
    """
    Audit trail of all changes to labor items
    Tracks status changes, assignments, updates, etc.
    """
    __tablename__ = "quote_labor_item_history"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Change tracking
    change_type = Column(String(50), nullable=False)  # status_change, contractor_assigned, time_logged, cost_updated, photo_added, note_added
    old_value = Column(Text)
    new_value = Column(Text)

    # Change details
    changed_by = Column(String(255))
    changed_by_type = Column(String(50))  # contractor, staff, customer, system
    change_reason = Column(Text)

    # Metadata
    change_metadata = Column(JSONB, default=dict)  # Renamed from 'metadata' (reserved in SQLAlchemy)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="history")

    __table_args__ = (
        Index('idx_labor_history_item_id', 'labor_item_id'),
        Index('idx_labor_history_type', 'change_type'),
        Index('idx_labor_history_created_at', 'created_at'),
    )


class QuoteLaborBeforeAfterPair(Base):
    """
    Paired before/after photos showing work completion and quality
    Includes measurements, improvements, annotations
    """
    __tablename__ = "quote_labor_before_after_pairs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    labor_item_id = Column(GUID, ForeignKey('quote_labor_items.id', ondelete='CASCADE'), nullable=False)

    # Photo references
    before_photo_id = Column(GUID, ForeignKey('quote_labor_item_photos.id', ondelete='SET NULL'))
    after_photo_id = Column(GUID, ForeignKey('quote_labor_item_photos.id', ondelete='SET NULL'))

    # Comparison details
    pair_title = Column(String(255))
    pair_description = Column(Text)
    work_performed = Column(Text)

    # Metrics/measurements
    before_measurement = Column(Numeric(10, 2))
    after_measurement = Column(Numeric(10, 2))
    improvement_percentage = Column(Numeric(5, 2))
    measurement_unit = Column(String(50))

    # Display
    display_order = Column(Integer, default=0)
    show_to_customer = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)

    # Annotations
    before_annotations = Column(JSONB)
    after_annotations = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    labor_item = relationship("QuoteLaborItem", back_populates="before_after_pairs")
    before_photo = relationship("QuoteLaborItemPhoto", foreign_keys=[before_photo_id])
    after_photo = relationship("QuoteLaborItemPhoto", foreign_keys=[after_photo_id])

    __table_args__ = (
        Index('idx_before_after_item_id', 'labor_item_id'),
        Index('idx_before_after_display_order', 'labor_item_id', 'display_order'),
    )


class ContractorWorkExample(Base):
    """
    Portfolio of example work by contractors to show customers
    Reference library of past successful projects
    """
    __tablename__ = "contractor_work_examples"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='CASCADE'))

    # Example details
    example_title = Column(String(255), nullable=False)
    example_description = Column(Text)
    work_category = Column(String(100))
    difficulty_level = Column(String(50))  # simple, moderate, complex

    # Photos
    primary_photo_url = Column(Text, nullable=False)
    additional_photos = Column(JSONB, default=list)

    # Project details
    project_type = Column(String(100))
    completion_date = Column(Date)
    duration_days = Column(Integer)
    total_cost = Column(Numeric(10, 2))

    # Skills showcased
    skills_demonstrated = Column(JSONB, default=list)
    equipment_used = Column(JSONB, default=list)

    # Customer info (anonymized)
    customer_satisfaction_rating = Column(Integer)  # 1-5
    customer_testimonial = Column(Text)

    # Display settings
    is_public = Column(Boolean, default=True)
    show_in_portfolio = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # Quality
    approved = Column(Boolean, default=False)
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contractor = relationship("Contractor", back_populates="work_examples")

    __table_args__ = (
        Index('idx_work_examples_contractor', 'contractor_id'),
        Index('idx_work_examples_category', 'work_category'),
    )


# Update the existing QuoteLaborItem model to add relationships
# This would be added to the existing models_quotes.py file:
"""
# Add to QuoteLaborItem class in models_quotes.py:

# Contractor assignment
assigned_contractor_id = Column(GUID, ForeignKey('contractors.id', ondelete='SET NULL'))
contractor_assigned_at = Column(DateTime(timezone=True))
contractor_assigned_by = Column(String(255))

# Work status tracking
work_status = Column(String(50), default='pending')
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
work_location_coords = Column(JSONB)  # {"lat": x, "lng": y}
work_location_address = Column(Text)

# Equipment/tools used
equipment_used = Column(JSONB, default=list)

# Additional metadata
weather_conditions = Column(Text)
access_notes = Column(Text)
safety_notes = Column(Text)

# Relationships
assigned_contractor = relationship("Contractor")
photos = relationship("QuoteLaborItemPhoto", back_populates="labor_item", cascade="all, delete-orphan")
notes = relationship("QuoteLaborItemNote", back_populates="labor_item", cascade="all, delete-orphan")
time_entries = relationship("QuoteLaborTimeEntry", back_populates="labor_item", cascade="all, delete-orphan")
materials_used = relationship("QuoteLaborMaterialUsed", back_populates="labor_item", cascade="all, delete-orphan")
history = relationship("QuoteLaborItemHistory", back_populates="labor_item", cascade="all, delete-orphan")
before_after_pairs = relationship("QuoteLaborBeforeAfterPair", back_populates="labor_item", cascade="all, delete-orphan")

# Add constraint
__table_args__ = (
    ...,  # existing constraints
    CheckConstraint("work_status IN ('pending', 'assigned', 'in_progress', 'completed', 'on_hold', 'cancelled', 'needs_review')"),
)
"""
