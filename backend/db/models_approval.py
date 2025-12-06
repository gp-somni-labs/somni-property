"""
Somni Property Manager - Approval Workflow Models
SQLAlchemy ORM models for human-in-the-middle approval system
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID, JSONB
from db.models import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Source
    source_type = Column(String(50), nullable=False)
    source_message_id = Column(GUID)
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='SET NULL'))

    # Requester
    requester_type = Column(String(50), nullable=False)
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    contractor_id = Column(GUID, ForeignKey('service_contractors.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='SET NULL'))
    requester_name = Column(String(255))
    requester_contact = Column(String(255))

    # Action Details
    action_type = Column(String(100), nullable=False)
    action_category = Column(String(50), nullable=False)
    action_title = Column(Text, nullable=False)
    action_description = Column(Text, nullable=False)
    action_data = Column(JSONB, nullable=False)

    # AI Analysis
    ai_intent = Column(String(100))
    ai_confidence = Column(Numeric(5, 4))
    ai_suggested_action = Column(Text)
    ai_risk_assessment = Column(String(50))
    ai_reasoning = Column(Text)

    # Urgency & Priority
    urgency = Column(String(50), default='normal')
    priority = Column(Integer, default=3)
    estimated_cost = Column(Numeric(10, 2))

    # Approval Status
    status = Column(String(50), default='pending')
    requires_multi_approval = Column(Boolean, default=False)
    approval_count_required = Column(Integer, default=1)
    approval_count_current = Column(Integer, default=0)

    # Auto-Approval
    can_auto_approve = Column(Boolean, default=False)
    auto_approve_reason = Column(String(255))
    auto_approved_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Approval/Rejection
    approved_by = Column(GUID, ForeignKey('tenants.id'))
    approved_at = Column(DateTime(timezone=True))
    rejected_by = Column(GUID, ForeignKey('tenants.id'))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Execution
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime(timezone=True))
    execution_result = Column(JSONB)
    execution_error = Column(Text)

    # Notification Tracking
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    reminder_sent_count = Column(Integer, default=0)
    last_reminder_sent_at = Column(DateTime(timezone=True))

    # Metadata
    extra_metadata = Column(JSONB)
    notes = Column(Text)

    # Relationships
    approval_actions = relationship("ApprovalAction", back_populates="pending_action", cascade="all, delete-orphan")
    notifications = relationship("ApprovalNotification", back_populates="pending_action", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("source_type IN ('email', 'sms', 'web', 'api')", name='valid_source_type'),
        CheckConstraint("requester_type IN ('tenant', 'contractor', 'landlord', 'client', 'system')", name='valid_requester_type'),
        CheckConstraint("urgency IN ('low', 'normal', 'high', 'critical', 'emergency')", name='valid_urgency'),
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')", name='valid_status'),
        Index('idx_pending_actions_status', 'status'),
        Index('idx_pending_actions_action_type', 'action_type'),
        Index('idx_pending_actions_urgency', 'urgency'),
        Index('idx_pending_actions_created', 'created_at'),
    )


class ApprovalAction(Base):
    __tablename__ = "approval_actions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    pending_action_id = Column(GUID, ForeignKey('pending_actions.id', ondelete='CASCADE'), nullable=False)

    # Approver
    approver_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    approver_name = Column(String(255))
    approver_role = Column(String(100))

    # Decision
    decision = Column(String(50), nullable=False)
    decision_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Reasoning
    reason = Column(Text)
    conditions = Column(Text)
    modifications = Column(JSONB)

    # Delegation
    delegated_to = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    delegated_at = Column(DateTime(timezone=True))

    # Notification
    notification_method = Column(String(50))
    response_time_seconds = Column(Integer)

    # Metadata
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pending_action = relationship("PendingAction", back_populates="approval_actions")

    __table_args__ = (
        CheckConstraint("decision IN ('approve', 'reject', 'request_info', 'delegate')", name='valid_decision'),
        Index('idx_approval_actions_pending', 'pending_action_id'),
        Index('idx_approval_actions_approver', 'approver_id'),
    )


class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    policy_name = Column(String(255), nullable=False, unique=True)
    policy_description = Column(Text)

    # Scope
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'))
    applies_to_all_properties = Column(Boolean, default=False)

    # Conditions
    action_types = Column(Text, nullable=False)  # JSON array
    requester_types = Column(Text)  # JSON array
    urgency_levels = Column(Text)  # JSON array
    max_estimated_cost = Column(Numeric(10, 2))

    # Auto-Approval Logic
    auto_approve_enabled = Column(Boolean, default=False)
    auto_approve_conditions = Column(JSONB)

    # Approval Requirements
    requires_approval = Column(Boolean, default=True)
    requires_multi_approval = Column(Boolean, default=False)
    approval_count_required = Column(Integer, default=1)
    approved_roles = Column(Text)  # JSON array

    # Time Limits
    approval_timeout_hours = Column(Integer)
    business_hours_only = Column(Boolean, default=False)

    # Notification Settings
    notify_on_creation = Column(Boolean, default=True)
    notify_on_approval = Column(Boolean, default=True)
    notify_on_rejection = Column(Boolean, default=True)
    escalation_after_hours = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=100)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))

    __table_args__ = (
        Index('idx_approval_policies_active', 'is_active'),
        Index('idx_approval_policies_priority', 'priority'),
    )


class ApprovalNotification(Base):
    __tablename__ = "approval_notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    pending_action_id = Column(GUID, ForeignKey('pending_actions.id', ondelete='CASCADE'), nullable=False)

    # Notification Details
    notification_type = Column(String(50), nullable=False)
    notification_channel = Column(String(50), nullable=False)

    # Recipients
    recipient_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    recipient_contact = Column(String(255))

    # Content
    notification_title = Column(Text)
    notification_body = Column(Text)
    notification_data = Column(JSONB)

    # Delivery Status
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime(timezone=True))
    read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    clicked = Column(Boolean, default=False)
    clicked_at = Column(DateTime(timezone=True))

    # Provider Details
    provider_message_id = Column(String(500))
    provider_status = Column(String(100))
    provider_error = Column(Text)

    # Metadata
    extra_metadata = Column(JSONB)

    # Relationships
    pending_action = relationship("PendingAction", back_populates="notifications")

    __table_args__ = (
        CheckConstraint("notification_type IN ('creation', 'reminder', 'approval', 'rejection', 'execution', 'expiration')", name='valid_notification_type'),
        CheckConstraint("notification_channel IN ('gotify', 'ntfy', 'email', 'sms')", name='valid_notification_channel'),
        Index('idx_approval_notifications_pending', 'pending_action_id'),
        Index('idx_approval_notifications_channel', 'notification_channel'),
    )
