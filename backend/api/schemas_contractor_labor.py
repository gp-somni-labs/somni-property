"""
Pydantic Schemas for Contractor Labor Documentation API
Comprehensive schemas for photos, notes, time tracking, materials, and before/after pairs
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from uuid import UUID
from decimal import Decimal


# ============================================================================
# PHOTO DOCUMENTATION SCHEMAS
# ============================================================================

class QuoteLaborItemPhotoBase(BaseModel):
    """Base schema for labor item photos"""
    photo_type: str = Field(..., description="Photo type: before, after, progress, issue, safety, equipment, completed")
    caption: Optional[str] = None
    description: Optional[str] = None
    photo_taken_by: Optional[str] = None
    photographer_type: Optional[str] = Field(None, description="contractor, staff, customer")
    location_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    related_task: Optional[str] = None
    annotations: List[Dict[str, Any]] = Field(default_factory=list, description="Image markup/annotations")
    display_order: int = 0
    show_to_customer: bool = True
    show_in_pdf: bool = True


class QuoteLaborItemPhotoCreate(QuoteLaborItemPhotoBase):
    """Schema for creating a new photo"""
    labor_item_id: UUID
    file_url: str = Field(..., description="URL to uploaded photo file")
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    gps_coordinates: Optional[Dict[str, float]] = Field(None, description="{'lat': 40.7128, 'lng': -74.0060}")


class QuoteLaborItemPhotoUpdate(BaseModel):
    """Schema for updating a photo"""
    caption: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    annotations: Optional[List[Dict[str, Any]]] = None
    display_order: Optional[int] = None
    show_to_customer: Optional[bool] = None
    show_in_pdf: Optional[bool] = None
    approved_for_display: Optional[bool] = None


class QuoteLaborItemPhoto(QuoteLaborItemPhotoBase):
    """Schema for returning photo data"""
    id: UUID
    labor_item_id: UUID
    file_url: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    photo_taken_at: datetime
    gps_coordinates: Optional[Dict[str, float]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    is_thumbnail: bool = False
    approved_for_display: bool = True
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# NOTES & COMMUNICATION SCHEMAS
# ============================================================================

class QuoteLaborItemNoteBase(BaseModel):
    """Base schema for labor item notes"""
    note_type: str = Field(..., description="progress_update, issue, material_request, question, completion, customer_feedback")
    note_text: str = Field(..., min_length=1)
    note_title: Optional[str] = None
    is_internal: bool = Field(False, description="Internal notes hidden from customer")
    show_to_customer: bool = True
    requires_response: bool = False
    priority: Optional[str] = Field(None, description="low, normal, high, urgent")
    tags: List[str] = Field(default_factory=list)
    attached_photo_ids: List[UUID] = Field(default_factory=list)
    attached_files: List[Dict[str, Any]] = Field(default_factory=list)
    hours_worked: Optional[Decimal] = None
    work_date: Optional[date] = None
    location_name: Optional[str] = None


class QuoteLaborItemNoteCreate(QuoteLaborItemNoteBase):
    """Schema for creating a new note"""
    labor_item_id: UUID
    created_by: str
    created_by_type: str = Field(..., description="contractor, staff, customer, system")
    created_by_id: Optional[UUID] = None
    location_coords: Optional[Dict[str, float]] = None


class QuoteLaborItemNoteUpdate(BaseModel):
    """Schema for updating a note"""
    note_text: Optional[str] = None
    note_title: Optional[str] = None
    is_internal: Optional[bool] = None
    show_to_customer: Optional[bool] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None


class QuoteLaborItemNoteResponse(BaseModel):
    """Schema for responding to a note"""
    response_text: str = Field(..., min_length=1)
    responded_by: str


class QuoteLaborItemNote(QuoteLaborItemNoteBase):
    """Schema for returning note data"""
    id: UUID
    labor_item_id: UUID
    created_by: str
    created_by_type: str
    created_by_id: Optional[UUID] = None
    responded_to: bool = False
    responded_by: Optional[str] = None
    responded_at: Optional[datetime] = None
    response_text: Optional[str] = None
    location_coords: Optional[Dict[str, float]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# TIME TRACKING SCHEMAS
# ============================================================================

class QuoteLaborTimeEntryBase(BaseModel):
    """Base schema for time entries"""
    work_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Decimal = Field(..., gt=0, description="Total billable hours")
    worker_name: str
    worker_role: Optional[str] = Field(None, description="lead_tech, assistant, apprentice")
    work_description: Optional[str] = None
    tasks_completed: List[str] = Field(default_factory=list)
    hourly_rate: Optional[Decimal] = None
    billable: bool = True
    break_duration_hours: Decimal = Field(Decimal("0"), ge=0)
    notes: Optional[str] = None
    issues_encountered: Optional[str] = None


class QuoteLaborTimeEntryCreate(QuoteLaborTimeEntryBase):
    """Schema for creating a time entry (clock in/out)"""
    labor_item_id: UUID
    contractor_id: Optional[UUID] = None
    clock_in_location: Optional[Dict[str, float]] = Field(None, description="GPS coordinates")
    clock_out_location: Optional[Dict[str, float]] = None

    @field_validator('duration_hours')
    @classmethod
    def validate_duration(cls, v, values):
        """Ensure duration doesn't exceed reasonable limits"""
        if v > 24:
            raise ValueError("Duration cannot exceed 24 hours")
        return v


class QuoteLaborTimeEntryUpdate(BaseModel):
    """Schema for updating a time entry"""
    end_time: Optional[time] = None
    duration_hours: Optional[Decimal] = None
    work_description: Optional[str] = None
    tasks_completed: Optional[List[str]] = None
    notes: Optional[str] = None
    issues_encountered: Optional[str] = None


class QuoteLaborTimeEntryApproval(BaseModel):
    """Schema for approving time entries"""
    approved: bool
    approved_by: str
    notes: Optional[str] = None


class QuoteLaborTimeEntry(QuoteLaborTimeEntryBase):
    """Schema for returning time entry data"""
    id: UUID
    labor_item_id: UUID
    contractor_id: Optional[UUID] = None
    total_cost: Optional[Decimal] = None
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    clock_in_location: Optional[Dict[str, float]] = None
    clock_out_location: Optional[Dict[str, float]] = None
    verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MATERIALS TRACKING SCHEMAS
# ============================================================================

class QuoteLaborMaterialUsedBase(BaseModel):
    """Base schema for materials used"""
    material_name: str
    material_category: Optional[str] = Field(None, description="cable, mounting, electrical, plumbing, etc.")
    quantity_used: Decimal = Field(..., gt=0)
    unit_type: str = Field(..., description="ft, ea, box, roll, etc.")
    unit_cost: Optional[Decimal] = None
    vendor_name: Optional[str] = None
    purchase_order_number: Optional[str] = None
    receipt_photo_url: Optional[str] = None
    notes: Optional[str] = None
    reason_for_variance: Optional[str] = None


class QuoteLaborMaterialUsedCreate(QuoteLaborMaterialUsedBase):
    """Schema for creating a material usage record"""
    labor_item_id: UUID
    used_date: Optional[date] = None
    recorded_by: Optional[str] = None
    was_estimated: bool = False
    estimated_quantity: Optional[Decimal] = None


class QuoteLaborMaterialUsedUpdate(BaseModel):
    """Schema for updating a material usage record"""
    quantity_used: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    vendor_name: Optional[str] = None
    purchase_order_number: Optional[str] = None
    receipt_photo_url: Optional[str] = None
    notes: Optional[str] = None
    reason_for_variance: Optional[str] = None


class QuoteLaborMaterialUsed(QuoteLaborMaterialUsedBase):
    """Schema for returning material usage data"""
    id: UUID
    labor_item_id: UUID
    total_cost: Optional[Decimal] = None
    used_date: Optional[date] = None
    recorded_by: Optional[str] = None
    was_estimated: bool = False
    estimated_quantity: Optional[Decimal] = None
    quantity_variance: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# BEFORE/AFTER PAIR SCHEMAS
# ============================================================================

class QuoteLaborBeforeAfterPairBase(BaseModel):
    """Base schema for before/after photo pairs"""
    pair_title: Optional[str] = None
    pair_description: Optional[str] = None
    work_performed: Optional[str] = None
    before_measurement: Optional[Decimal] = None
    after_measurement: Optional[Decimal] = None
    improvement_percentage: Optional[Decimal] = None
    measurement_unit: Optional[str] = None
    display_order: int = 0
    show_to_customer: bool = True
    featured: bool = False
    before_annotations: Optional[Dict[str, Any]] = None
    after_annotations: Optional[Dict[str, Any]] = None


class QuoteLaborBeforeAfterPairCreate(QuoteLaborBeforeAfterPairBase):
    """Schema for creating a before/after pair"""
    labor_item_id: UUID
    before_photo_id: UUID
    after_photo_id: UUID


class QuoteLaborBeforeAfterPairUpdate(BaseModel):
    """Schema for updating a before/after pair"""
    pair_title: Optional[str] = None
    pair_description: Optional[str] = None
    work_performed: Optional[str] = None
    before_measurement: Optional[Decimal] = None
    after_measurement: Optional[Decimal] = None
    improvement_percentage: Optional[Decimal] = None
    measurement_unit: Optional[str] = None
    display_order: Optional[int] = None
    show_to_customer: Optional[bool] = None
    featured: Optional[bool] = None


class QuoteLaborBeforeAfterPair(QuoteLaborBeforeAfterPairBase):
    """Schema for returning before/after pair data"""
    id: UUID
    labor_item_id: UUID
    before_photo_id: Optional[UUID] = None
    after_photo_id: Optional[UUID] = None
    created_at: datetime
    # Nested photo objects for convenience
    before_photo: Optional[QuoteLaborItemPhoto] = None
    after_photo: Optional[QuoteLaborItemPhoto] = None

    class Config:
        from_attributes = True


# ============================================================================
# CONTRACTOR WORK EXAMPLE SCHEMAS
# ============================================================================

class ContractorWorkExampleBase(BaseModel):
    """Base schema for contractor work examples"""
    example_title: str
    example_description: Optional[str] = None
    work_category: Optional[str] = Field(None, description="smart_locks, electrical, plumbing, etc.")
    difficulty_level: Optional[str] = Field(None, description="simple, moderate, complex")
    project_type: Optional[str] = None
    completion_date: Optional[date] = None
    duration_days: Optional[int] = None
    total_cost: Optional[Decimal] = None
    skills_demonstrated: List[str] = Field(default_factory=list)
    equipment_used: List[str] = Field(default_factory=list)
    customer_satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    customer_testimonial: Optional[str] = None
    is_public: bool = True
    show_in_portfolio: bool = True
    display_order: int = 0


class ContractorWorkExampleCreate(ContractorWorkExampleBase):
    """Schema for creating a work example"""
    contractor_id: UUID
    primary_photo_url: str
    additional_photos: List[Dict[str, str]] = Field(default_factory=list, description="[{'url': '...', 'caption': '...'}]")


class ContractorWorkExampleUpdate(BaseModel):
    """Schema for updating a work example"""
    example_title: Optional[str] = None
    example_description: Optional[str] = None
    work_category: Optional[str] = None
    difficulty_level: Optional[str] = None
    additional_photos: Optional[List[Dict[str, str]]] = None
    skills_demonstrated: Optional[List[str]] = None
    equipment_used: Optional[List[str]] = None
    customer_testimonial: Optional[str] = None
    is_public: Optional[bool] = None
    show_in_portfolio: Optional[bool] = None
    display_order: Optional[int] = None


class ContractorWorkExampleApproval(BaseModel):
    """Schema for approving a work example"""
    approved: bool
    approved_by: str


class ContractorWorkExample(ContractorWorkExampleBase):
    """Schema for returning work example data"""
    id: UUID
    contractor_id: UUID
    primary_photo_url: str
    additional_photos: List[Dict[str, str]] = Field(default_factory=list)
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LABOR ITEM UPDATE SCHEMAS (Enhanced)
# ============================================================================

class QuoteLaborItemAssignment(BaseModel):
    """Schema for assigning contractor to labor item"""
    assigned_contractor_id: UUID
    contractor_assigned_by: str
    access_notes: Optional[str] = Field(None, description="Gate codes, parking, access instructions")
    safety_notes: Optional[str] = Field(None, description="Safety requirements and precautions")


class QuoteLaborItemStatusUpdate(BaseModel):
    """Schema for updating work status"""
    work_status: str = Field(..., description="assigned, in_progress, completed, on_hold, cancelled")
    status_notes: Optional[str] = None
    changed_by: str
    changed_by_type: str = Field(..., description="contractor, staff, system")


class QuoteLaborItemActuals(BaseModel):
    """Schema for updating actual costs and hours"""
    actual_hours: Decimal
    actual_labor_cost: Decimal
    actual_materials_cost: Decimal
    actual_total_cost: Decimal
    variance_explanation: str = Field(..., description="Explanation for any variance from estimate")


class QuoteLaborItemQC(BaseModel):
    """Schema for quality control approval"""
    qc_passed: bool
    qc_performed_by: str
    qc_notes: Optional[str] = None


class QuoteLaborItemCustomerApproval(BaseModel):
    """Schema for customer approval"""
    customer_approved: bool
    customer_approval_notes: Optional[str] = None


# ============================================================================
# COMPREHENSIVE REPORTING SCHEMAS
# ============================================================================

class LaborItemProgress(BaseModel):
    """Schema for labor item progress report"""
    labor_item_id: UUID
    task_name: str
    work_status: str
    progress_percentage: int = Field(..., ge=0, le=100)
    estimated_hours: Decimal
    actual_hours: Decimal
    hours_variance: Decimal
    estimated_cost: Decimal
    actual_cost: Decimal
    cost_variance: Decimal
    photo_count: int
    note_count: int
    time_entry_count: int
    last_update: datetime


class ContractorDashboard(BaseModel):
    """Schema for contractor dashboard data"""
    contractor_id: UUID
    contractor_name: str
    active_jobs_count: int
    completed_jobs_count: int
    total_hours_this_week: Decimal
    total_earnings_this_week: Decimal
    pending_approvals_count: int
    active_labor_items: List[LaborItemProgress]
    recent_notes: List[QuoteLaborItemNote]
    pending_time_entries: List[QuoteLaborTimeEntry]


class LaborCostAnalysis(BaseModel):
    """Schema for labor cost variance analysis"""
    quote_id: UUID
    total_estimated_hours: Decimal
    total_actual_hours: Decimal
    total_hours_variance: Decimal
    total_estimated_labor_cost: Decimal
    total_actual_labor_cost: Decimal
    total_labor_cost_variance: Decimal
    total_estimated_materials_cost: Decimal
    total_actual_materials_cost: Decimal
    total_materials_cost_variance: Decimal
    variance_by_category: Dict[str, Dict[str, Decimal]]
    major_variance_reasons: List[str]


# ============================================================================
# PHOTO UPLOAD SCHEMAS
# ============================================================================

class PhotoUploadResponse(BaseModel):
    """Response schema for photo upload"""
    file_url: str
    file_path: str
    file_size: int
    mime_type: str
    thumbnail_url: Optional[str] = None


class BulkPhotoUpload(BaseModel):
    """Schema for bulk photo upload"""
    labor_item_id: UUID
    photos: List[QuoteLaborItemPhotoCreate]


# ============================================================================
# FILTERING & PAGINATION
# ============================================================================

class PhotoFilter(BaseModel):
    """Filters for photo queries"""
    photo_type: Optional[str] = None
    show_to_customer: Optional[bool] = None
    approved_only: bool = True
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class NoteFilter(BaseModel):
    """Filters for note queries"""
    note_type: Optional[str] = None
    requires_response: Optional[bool] = None
    is_internal: Optional[bool] = None
    priority: Optional[str] = None
    created_by_type: Optional[str] = None


class TimeEntryFilter(BaseModel):
    """Filters for time entry queries"""
    approved: Optional[bool] = None
    billable: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    contractor_id: Optional[UUID] = None
