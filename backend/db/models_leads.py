"""
Somni Property Manager - Leads Database Models
Captures potential business opportunities from NoteCaptureMCP and other sources.
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean,
    Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID, JSONB


def get_base():
    """Import Base from models to avoid circular imports."""
    from db.models import Base
    return Base


Base = get_base()


class Lead(Base):
    """
    Lead model for capturing potential business opportunities.

    Leads can come from:
    - NoteCaptureMCP (conversations captured via Omi/Limitless pendants)
    - Website inquiries
    - Referrals
    - Manual entry

    Leads can be converted to full Clients once qualified and closed.
    """
    __tablename__ = "leads"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Contact Information
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))

    # Lead Source
    source = Column(String(50), nullable=False, default='manual')
    source_id = Column(String(255))  # External ID (e.g., Omi memory ID)
    obsidian_note_path = Column(String(512))  # Path to linked Obsidian note

    # Property Interest
    property_type = Column(String(50))  # residential, commercial, mixed-use
    property_location = Column(String(255))  # City/area of interest
    property_details = Column(Text)  # Free-text property description

    # Business Signals
    interest_level = Column(String(20), default='medium')  # low, medium, high
    timeline = Column(String(50))  # immediate, 1-3 months, 3-6 months, etc.
    budget_range = Column(String(100))
    services_interested = Column(JSONB, default=list)  # List of services

    # Lead Qualification
    status = Column(String(20), nullable=False, default='new')
    score = Column(Integer, default=50)  # Lead score 0-100

    # Conversation Context
    summary = Column(Text)  # AI-generated summary of the conversation
    key_points = Column(JSONB, default=list)  # Key points from conversation
    action_items = Column(JSONB, default=list)  # Action items identified

    # Follow-up
    next_action = Column(String(255))
    next_action_date = Column(DateTime(timezone=True))
    assigned_to = Column(String(255))  # Employee assigned to follow up

    # Conversion
    converted_to_client_id = Column(GUID, ForeignKey('clients.id', ondelete='SET NULL'))
    converted_at = Column(DateTime(timezone=True))

    # Extra Data
    notes = Column(Text)  # Internal notes
    tags = Column(JSONB, default=list)
    lead_metadata = Column(JSONB, default=dict)  # Additional data from source

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    contacted_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "source IN ('notecapture', 'website', 'referral', 'manual', 'import', 'other')",
            name='valid_lead_source'
        ),
        CheckConstraint(
            "status IN ('new', 'contacted', 'qualified', 'proposal', 'negotiation', 'converted', 'lost')",
            name='valid_lead_status'
        ),
        CheckConstraint(
            "interest_level IN ('low', 'medium', 'high')",
            name='valid_interest_level'
        ),
        Index('idx_leads_status', 'status'),
        Index('idx_leads_source', 'source'),
        Index('idx_leads_email', 'email'),
        Index('idx_leads_created_at', 'created_at'),
        Index('idx_leads_score', 'score'),
    )


class LeadActivity(Base):
    """
    Activity log for leads - tracks all interactions and updates.
    """
    __tablename__ = "lead_activities"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    lead_id = Column(GUID, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)

    # Activity Details
    activity_type = Column(String(50), nullable=False)  # note, call, email, meeting, status_change
    description = Column(Text)

    # Outcome
    outcome = Column(String(50))  # positive, negative, neutral
    next_steps = Column(Text)

    # User Info
    performed_by = Column(String(255))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_lead_activities_lead_id', 'lead_id'),
        Index('idx_lead_activities_type', 'activity_type'),
    )
