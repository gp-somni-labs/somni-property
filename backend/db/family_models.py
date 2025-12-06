"""
Family Mode Database Models
Models for SomniFamily MSP (Managed Service Provider) features
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .models import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration"""
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"


class TicketPriority(str, enum.Enum):
    """Support ticket priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, enum.Enum):
    """Support ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ============================================================================
# SUBSCRIPTION MODELS
# ============================================================================

class FamilySubscription(Base):
    """Family mode subscription tracking"""
    __tablename__ = "family_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)

    # Subscription details
    tier = Column(SQLEnum(SubscriptionTier, native_enum=False), nullable=False, default=SubscriptionTier.STARTER)
    status = Column(SQLEnum(SubscriptionStatus, native_enum=False), nullable=False, default=SubscriptionStatus.ACTIVE)

    # Pricing
    base_price = Column(Float, nullable=False)  # Monthly base price
    included_support_hours = Column(Integer, nullable=False)  # Hours included per month
    overage_rate = Column(Float, nullable=False)  # $/hour for overage

    # Billing
    billing_cycle_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    next_billing_date = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)

    # Add-ons
    addons = Column(JSONB, default={})  # { "addon_id": { "name": "...", "price": 100 } }

    # Dates
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="family_subscription")
    support_hours = relationship("SupportHours", back_populates="subscription", cascade="all, delete-orphan")
    support_tickets = relationship("FamilySupportTicket", back_populates="subscription", cascade="all, delete-orphan")
    billing_records = relationship("FamilyBilling", back_populates="subscription", cascade="all, delete-orphan")


# ============================================================================
# SUPPORT HOURS TRACKING
# ============================================================================

class SupportHours(Base):
    """Support hours usage tracking"""
    __tablename__ = "support_hours"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("family_subscriptions.id"), nullable=False)

    # Billing cycle
    billing_cycle_start = Column(DateTime, nullable=False)
    billing_cycle_end = Column(DateTime, nullable=False)

    # Hours tracking
    included_hours = Column(Integer, nullable=False)
    used_hours = Column(Float, default=0.0)
    overage_hours = Column(Float, default=0.0)

    # Cost tracking
    base_cost = Column(Float, default=0.0)
    overage_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # Metadata
    support_sessions = Column(JSONB, default=[])  # List of support session IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("FamilySubscription", back_populates="support_hours")


class SupportSession(Base):
    """Individual support session tracking"""
    __tablename__ = "support_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("family_subscriptions.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"), nullable=True)

    # Session details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    support_engineer = Column(String(255))  # Engineer who handled it

    # Time tracking
    duration_minutes = Column(Integer, nullable=False)
    duration_hours = Column(Float, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)

    # Billing
    billable = Column(Boolean, default=True)
    hourly_rate = Column(Float)
    total_cost = Column(Float)

    # Notes
    notes = Column(Text)
    work_performed = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# SUPPORT TICKETS
# ============================================================================

class FamilySupportTicket(Base):
    """Family mode support tickets"""
    __tablename__ = "family_support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("family_subscriptions.id"), nullable=False)

    # Ticket details
    ticket_number = Column(String(50), unique=True, nullable=False)  # e.g., "FAM-2025-001"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Classification
    priority = Column(SQLEnum(TicketPriority, native_enum=False), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(SQLEnum(TicketStatus, native_enum=False), nullable=False, default=TicketStatus.OPEN)
    category = Column(String(100))  # e.g., "automation", "device", "billing", "general"

    # Assignment
    assigned_to = Column(String(255))  # Support engineer email/name
    assigned_at = Column(DateTime)

    # Response tracking
    first_response_at = Column(DateTime)
    resolved_at = Column(DateTime)
    closed_at = Column(DateTime)

    # SLA tracking
    sla_response_time_hours = Column(Integer)  # Expected response time
    sla_resolution_time_hours = Column(Integer)  # Expected resolution time
    sla_response_breached = Column(Boolean, default=False)
    sla_resolution_breached = Column(Boolean, default=False)

    # Customer info
    customer_name = Column(String(255))
    customer_email = Column(String(255))
    customer_phone = Column(String(50))

    # Technical details
    device_id = Column(UUID(as_uuid=True), ForeignKey("smart_devices.id"), nullable=True)
    hub_id = Column(UUID(as_uuid=True), ForeignKey("property_edge_nodes.id"), nullable=True)
    error_logs = Column(Text)

    # Metadata
    tags = Column(JSONB, default=[])
    attachments = Column(JSONB, default=[])  # List of attachment URLs
    internal_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("FamilySubscription", back_populates="support_tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")


class TicketComment(Base):
    """Support ticket comments/updates"""
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("family_support_tickets.id"), nullable=False)

    # Comment details
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    author_type = Column(String(50), nullable=False)  # "customer", "engineer", "system"

    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # Internal notes vs customer-visible

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship("FamilySupportTicket", back_populates="comments")


# ============================================================================
# ALERTS & MONITORING
# ============================================================================

class FamilyAlert(Base):
    """Family mode alerts and notifications"""
    __tablename__ = "family_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("family_subscriptions.id"), nullable=False)

    # Alert details
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverity, native_enum=False), nullable=False, default=AlertSeverity.INFO)
    status = Column(SQLEnum(AlertStatus, native_enum=False), nullable=False, default=AlertStatus.ACTIVE)

    # Source
    source_type = Column(String(100))  # "device", "hub", "automation", "system"
    source_id = Column(String(255))  # ID of the source entity
    source_name = Column(String(255))  # Friendly name

    # Device info
    device_id = Column(UUID(as_uuid=True), ForeignKey("smart_devices.id"), nullable=True)
    hub_id = Column(UUID(as_uuid=True), ForeignKey("property_edge_nodes.id"), nullable=True)

    # Response tracking
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(255))
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolution_notes = Column(Text)

    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_to_ticket = Column(UUID(as_uuid=True), ForeignKey("family_support_tickets.id"), nullable=True)
    escalated_at = Column(DateTime)

    # Notification tracking
    notifications_sent = Column(JSONB, default=[])  # List of notification methods sent

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# BILLING
# ============================================================================

class FamilyBilling(Base):
    """Family mode billing records"""
    __tablename__ = "family_billing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("family_subscriptions.id"), nullable=False)

    # Billing period
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    invoice_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    billing_date = Column(DateTime, nullable=False, default=datetime.utcnow)  # Alias for analytics compatibility
    due_date = Column(DateTime, nullable=False)

    # Amounts
    base_subscription = Column(Float, nullable=False)
    addons_total = Column(Float, default=0.0)
    support_hours_base = Column(Float, default=0.0)
    support_hours_overage = Column(Float, default=0.0)
    custom_services = Column(Float, default=0.0)
    hardware_charges = Column(Float, default=0.0)

    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    amount_due = Column(Float, nullable=False)  # Alias for analytics compatibility

    # Payment
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime)
    payment_method = Column(String(100))
    transaction_id = Column(String(255))

    # Line items
    line_items = Column(JSONB, default=[])  # Detailed breakdown

    # Status
    status = Column(String(50), default="pending")  # pending, paid, overdue, cancelled

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("FamilySubscription", back_populates="billing_records")


# ============================================================================
# AUTOMATION LIBRARY
# ============================================================================

class AutomationTemplate(Base):
    """Pre-built automation templates available to Family customers"""
    __tablename__ = "automation_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # "security", "comfort", "energy", "convenience"

    # Requirements
    required_devices = Column(JSONB, default=[])  # List of device types needed
    tier_requirement = Column(SQLEnum(SubscriptionTier, native_enum=False), default=SubscriptionTier.STARTER)

    # Pricing
    is_premium = Column(Boolean, default=False)
    setup_fee = Column(Float, default=0.0)
    monthly_fee = Column(Float, default=0.0)

    # Configuration
    ha_automation_yaml = Column(Text)  # Home Assistant automation YAML
    configuration_schema = Column(JSONB)  # JSON Schema for user configuration

    # Metadata
    icon = Column(String(100))
    thumbnail_url = Column(String(500))
    popularity_score = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
