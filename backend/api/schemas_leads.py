"""
Somni Property Manager - Lead Pydantic Schemas
Request/response models for leads API
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# LEAD SCHEMAS
# ============================================================================

class LeadBase(BaseModel):
    """Base schema for leads with common fields."""
    name: str = Field(..., max_length=255, description="Lead contact name")
    email: Optional[EmailStr] = Field(None, description="Lead email address")
    phone: Optional[str] = Field(None, max_length=50, description="Lead phone number")
    company: Optional[str] = Field(None, max_length=255, description="Company name")


class LeadCreate(LeadBase):
    """Schema for creating a new lead."""
    # Source information
    source: str = Field(
        default='manual',
        pattern="^(notecapture|website|referral|manual|import|other)$",
        description="Lead source"
    )
    source_id: Optional[str] = Field(None, max_length=255, description="External source ID")
    obsidian_note_path: Optional[str] = Field(None, max_length=512, description="Path to Obsidian note")

    # Property interest
    property_type: Optional[str] = Field(
        None,
        pattern="^(residential|commercial|mixed-use)$",
        description="Type of property interested in"
    )
    property_location: Optional[str] = Field(None, max_length=255, description="Preferred location")
    property_details: Optional[str] = Field(None, description="Property requirements details")

    # Business signals
    interest_level: Optional[str] = Field(
        default='medium',
        pattern="^(low|medium|high)$",
        description="Interest level"
    )
    timeline: Optional[str] = Field(None, max_length=50, description="Timeline for decision")
    budget_range: Optional[str] = Field(None, max_length=100, description="Budget range")
    services_interested: Optional[List[str]] = Field(default_factory=list, description="Services interested in")

    # Conversation context (from NoteCaptureMCP)
    summary: Optional[str] = Field(None, description="AI-generated summary")
    key_points: Optional[List[str]] = Field(default_factory=list, description="Key points from conversation")
    action_items: Optional[List[str]] = Field(default_factory=list, description="Action items identified")

    # Additional data
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    lead_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional lead metadata")


class LeadUpdate(BaseModel):
    """Schema for updating an existing lead."""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=255)

    # Status and qualification
    status: Optional[str] = Field(
        None,
        pattern="^(new|contacted|qualified|proposal|negotiation|converted|lost)$",
        description="Lead status"
    )
    score: Optional[int] = Field(None, ge=0, le=100, description="Lead score 0-100")
    interest_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")

    # Property interest
    property_type: Optional[str] = Field(None, pattern="^(residential|commercial|mixed-use)$")
    property_location: Optional[str] = Field(None, max_length=255)
    property_details: Optional[str] = None

    # Business details
    timeline: Optional[str] = Field(None, max_length=50)
    budget_range: Optional[str] = Field(None, max_length=100)
    services_interested: Optional[List[str]] = None

    # Follow-up
    next_action: Optional[str] = Field(None, max_length=255)
    next_action_date: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=255)

    # Notes
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class Lead(LeadBase):
    """Full lead schema for API responses."""
    id: UUID
    source: str
    source_id: Optional[str] = None
    obsidian_note_path: Optional[str] = None

    # Property interest
    property_type: Optional[str] = None
    property_location: Optional[str] = None
    property_details: Optional[str] = None

    # Business signals
    interest_level: str
    timeline: Optional[str] = None
    budget_range: Optional[str] = None
    services_interested: List[str] = []

    # Status and qualification
    status: str
    score: int

    # Conversation context
    summary: Optional[str] = None
    key_points: List[str] = []
    action_items: List[str] = []

    # Follow-up
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

    # Conversion
    converted_to_client_id: Optional[UUID] = None
    converted_at: Optional[datetime] = None

    # Additional Data
    notes: Optional[str] = None
    tags: List[str] = []
    lead_metadata: Dict[str, Any] = {}

    # Timestamps
    created_at: datetime
    updated_at: datetime
    contacted_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    """Response schema for lead list with pagination."""
    total: int
    items: List[Lead]
    skip: int
    limit: int


# ============================================================================
# LEAD ACTIVITY SCHEMAS
# ============================================================================

class LeadActivityCreate(BaseModel):
    """Schema for creating a lead activity."""
    activity_type: str = Field(
        ...,
        pattern="^(note|call|email|meeting|status_change|follow_up|other)$",
        description="Type of activity"
    )
    description: Optional[str] = Field(None, description="Activity description")
    outcome: Optional[str] = Field(
        None,
        pattern="^(positive|negative|neutral)$",
        description="Outcome of activity"
    )
    next_steps: Optional[str] = Field(None, description="Next steps after this activity")
    performed_by: Optional[str] = Field(None, max_length=255, description="Who performed the activity")


class LeadActivity(BaseModel):
    """Full lead activity schema for API responses."""
    id: UUID
    lead_id: UUID
    activity_type: str
    description: Optional[str] = None
    outcome: Optional[str] = None
    next_steps: Optional[str] = None
    performed_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# NOTECAPTURE INTEGRATION SCHEMAS
# ============================================================================

class NoteCaptureLead(BaseModel):
    """
    Schema for leads coming from NoteCaptureMCP.

    This is the format that NoteCaptureMCP's SomniPropertyIntegration
    will use when creating leads from captured conversations.
    """
    # Contact extracted from conversation
    name: str = Field(..., description="Contact name from conversation")
    email: Optional[EmailStr] = Field(None, description="Email if mentioned")
    phone: Optional[str] = Field(None, description="Phone if mentioned")
    company: Optional[str] = Field(None, description="Company if mentioned")

    # Property interest
    property_interest: Optional[str] = Field(None, description="Property interest description")
    property_type: Optional[str] = Field(None, description="Type of property")
    property_location: Optional[str] = Field(None, description="Location mentioned")

    # Context from NoteCaptureMCP
    source_id: Optional[str] = Field(None, description="Omi/Limitless ID")
    obsidian_path: Optional[str] = Field(None, description="Path to Obsidian note")
    summary: Optional[str] = Field(None, description="AI summary of conversation")
    key_points: List[str] = Field(default_factory=list, description="Key points")
    action_items: List[str] = Field(default_factory=list, description="Action items")

    # Business signals from NoteCaptureMCP
    business_signals: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Business signals detected (type, description, confidence)"
    )

    # Metadata
    raw_content: Optional[str] = Field(None, description="Raw conversation content")
    capture_timestamp: Optional[datetime] = Field(None, description="When conversation was captured")


class NoteCaptureleadResponse(BaseModel):
    """Response for NoteCaptureMCP lead creation."""
    status: str = Field(..., description="success or error")
    lead_id: Optional[UUID] = Field(None, description="Created lead ID")
    message: str = Field(..., description="Status message")
    external_id: Optional[str] = Field(None, description="Lead ID for external reference")
