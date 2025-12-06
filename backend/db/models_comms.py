"""
Somni Property Manager - Agentic Communication Models
SQLAlchemy ORM models for email and SMS communication
"""

from sqlalchemy import (
    Column, String, Integer, Numeric, Date, DateTime, Boolean,
    Text, ForeignKey, CheckConstraint, UniqueConstraint, Index, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID, JSONB

# Import base from main models
from db.models import Base


# ============================================================================
# EMAIL COMMUNICATION MODELS
# ============================================================================

class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'))
    account_type = Column(String(50), nullable=False)
    email_address = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)

    # IMAP Configuration
    imap_host = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993)
    imap_use_ssl = Column(Boolean, default=True)
    imap_username = Column(String(255), nullable=False)
    imap_password_encrypted = Column(Text, nullable=False)
    imap_folder = Column(String(255), default='INBOX')

    # SMTP Configuration
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_use_tls = Column(Boolean, default=True)
    smtp_username = Column(String(255), nullable=False)
    smtp_password_encrypted = Column(Text, nullable=False)

    # Configuration
    auto_reply_enabled = Column(Boolean, default=True)
    ai_agent_enabled = Column(Boolean, default=True)
    signature = Column(Text)
    max_auto_reply_confidence = Column(Numeric(3, 2), default=0.85)
    escalation_email = Column(String(255))
    polling_interval_minutes = Column(Integer, default=2)

    # Status
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime(timezone=True))
    last_email_sent = Column(DateTime(timezone=True))
    total_emails_processed = Column(Integer, default=0)
    total_auto_replies = Column(Integer, default=0)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", backref="email_accounts")
    building = relationship("Building", backref="email_accounts")
    messages = relationship("EmailMessage", back_populates="account", cascade="all, delete-orphan")
    threads = relationship("EmailThread", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('tenant_support', 'contractor_coordination', 'general', 'emergency')",
            name='valid_email_account_type'
        ),
        Index('idx_email_accounts_property', 'property_id'),
        Index('idx_email_accounts_active', 'is_active'),
    )


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email_account_id = Column(GUID, ForeignKey('email_accounts.id', ondelete='CASCADE'), nullable=False)
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='SET NULL'))

    # Email Headers
    message_id = Column(String(500), unique=True, nullable=False)
    in_reply_to = Column(String(500))
    references = Column(Text)
    thread_id = Column(String(255))

    # Direction
    direction = Column(String(20), nullable=False)

    # Addresses
    from_address = Column(String(255), nullable=False)
    from_name = Column(String(255))
    to_addresses = Column(Text, nullable=False)  # JSON array
    cc_addresses = Column(Text)
    bcc_addresses = Column(Text)
    reply_to = Column(String(255))

    # Content
    subject = Column(Text, nullable=False)
    body_text = Column(Text)
    body_html = Column(Text)
    snippet = Column(Text)

    # Attachments
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    attachment_metadata = Column(JSONB)

    # Processing
    received_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    is_read = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)

    # AI Processing
    ai_processed = Column(Boolean, default=False)
    ai_intent = Column(String(100))
    ai_confidence = Column(Numeric(5, 4))
    ai_entities = Column(JSONB)
    ai_sentiment = Column(String(50))
    ai_requires_human = Column(Boolean, default=False)
    ai_auto_replied = Column(Boolean, default=False)

    # Classification
    message_category = Column(String(100))
    priority = Column(String(50), default='normal')
    is_spam = Column(Boolean, default=False)
    spam_score = Column(Numeric(5, 4))

    # Associations
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))
    contractor_id = Column(GUID, ForeignKey('service_contractors.id', ondelete='SET NULL'))

    # Actions
    work_order_created = Column(GUID, ForeignKey('work_orders.id'))
    payment_link_sent = Column(Boolean, default=False)
    escalated_to_human = Column(Boolean, default=False)
    escalated_at = Column(DateTime(timezone=True))

    # Metadata
    raw_headers = Column(JSONB)
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    account = relationship("EmailAccount", back_populates="messages")
    conversation = relationship("AIConversation", backref="email_messages")
    tenant = relationship("Tenant", backref="email_messages")
    unit = relationship("Unit", backref="email_messages")

    __table_args__ = (
        CheckConstraint("direction IN ('incoming', 'outgoing')", name='valid_email_direction'),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='valid_email_priority'),
        Index('idx_email_messages_account', 'email_account_id'),
        Index('idx_email_messages_conversation', 'conversation_id'),
        Index('idx_email_messages_direction', 'direction'),
        Index('idx_email_messages_received', 'received_at'),
        Index('idx_email_messages_tenant', 'tenant_id'),
    )


class EmailThread(Base):
    __tablename__ = "email_threads"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email_account_id = Column(GUID, ForeignKey('email_accounts.id', ondelete='CASCADE'), nullable=False)
    thread_subject = Column(String(500))
    participant_emails = Column(Text, nullable=False)  # JSON array

    # Classification
    thread_category = Column(String(100))
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))

    # Status
    status = Column(String(50), default='active')
    message_count = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)

    # Timestamps
    first_message_at = Column(DateTime(timezone=True))
    last_message_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Metadata
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    account = relationship("EmailAccount", back_populates="threads")
    tenant = relationship("Tenant", backref="email_threads")
    unit = relationship("Unit", backref="email_threads")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'resolved', 'escalated', 'archived')",
            name='valid_thread_status'
        ),
        Index('idx_email_threads_account', 'email_account_id'),
        Index('idx_email_threads_status', 'status'),
    )


# ============================================================================
# SMS COMMUNICATION MODELS
# ============================================================================

class SMSNumber(Base):
    __tablename__ = "sms_numbers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    property_id = Column(GUID, ForeignKey('properties.id', ondelete='CASCADE'))
    building_id = Column(GUID, ForeignKey('buildings.id', ondelete='CASCADE'))

    # Phone Number
    phone_number = Column(String(20), nullable=False, unique=True)
    friendly_name = Column(String(255))
    number_type = Column(String(50), default='tenant_support')

    # Provider Configuration
    provider = Column(String(50), nullable=False, default='twilio')
    account_sid = Column(String(255), nullable=False)
    auth_token_encrypted = Column(Text, nullable=False)
    api_endpoint = Column(String(500))

    # Configuration
    auto_reply_enabled = Column(Boolean, default=True)
    ai_agent_enabled = Column(Boolean, default=True)
    max_auto_reply_confidence = Column(Numeric(3, 2), default=0.80)
    business_hours_only = Column(Boolean, default=False)
    business_hours_start = Column(Time, default='09:00:00')
    business_hours_end = Column(Time, default='17:00:00')
    business_days = Column(Text, default='1,2,3,4,5')

    # Status
    is_active = Column(Boolean, default=True)
    webhook_url = Column(String(500))
    last_message_received = Column(DateTime(timezone=True))
    last_message_sent = Column(DateTime(timezone=True))
    total_messages_received = Column(Integer, default=0)
    total_messages_sent = Column(Integer, default=0)
    total_auto_replies = Column(Integer, default=0)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", backref="sms_numbers")
    building = relationship("Building", backref="sms_numbers")
    messages = relationship("SMSMessage", back_populates="sms_number", cascade="all, delete-orphan")
    conversations = relationship("SMSConversation", back_populates="sms_number", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "number_type IN ('tenant_support', 'contractor', 'emergency', 'general')",
            name='valid_sms_number_type'
        ),
        CheckConstraint(
            "provider IN ('twilio', 'vonage', 'signalwire')",
            name='valid_sms_provider'
        ),
        Index('idx_sms_numbers_property', 'property_id'),
        Index('idx_sms_numbers_active', 'is_active'),
    )


class SMSMessage(Base):
    __tablename__ = "sms_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    sms_number_id = Column(GUID, ForeignKey('sms_numbers.id', ondelete='CASCADE'), nullable=False)
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='SET NULL'))

    # Direction
    direction = Column(String(20), nullable=False)

    # Phone Numbers
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)

    # Content
    message_body = Column(Text, nullable=False)
    message_length = Column(Integer)

    # Media (MMS)
    has_media = Column(Boolean, default=False)
    media_count = Column(Integer, default=0)
    media_urls = Column(JSONB)
    media_metadata = Column(JSONB)

    # Provider Data
    provider_message_sid = Column(String(255), unique=True)
    provider_status = Column(String(50))
    provider_error_code = Column(String(50))
    provider_error_message = Column(Text)

    # Processing
    received_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    is_read = Column(Boolean, default=False)

    # AI Processing
    ai_processed = Column(Boolean, default=False)
    ai_intent = Column(String(100))
    ai_confidence = Column(Numeric(5, 4))
    ai_entities = Column(JSONB)
    ai_sentiment = Column(String(50))
    ai_requires_human = Column(Boolean, default=False)
    ai_auto_replied = Column(Boolean, default=False)

    # Classification
    message_category = Column(String(100))
    priority = Column(String(50), default='normal')
    is_spam = Column(Boolean, default=False)

    # Associations
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))
    contractor_id = Column(GUID, ForeignKey('service_contractors.id', ondelete='SET NULL'))

    # Actions
    work_order_created = Column(GUID, ForeignKey('work_orders.id'))
    payment_link_sent = Column(Boolean, default=False)
    escalated_to_human = Column(Boolean, default=False)
    escalated_at = Column(DateTime(timezone=True))

    # Metadata
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sms_number = relationship("SMSNumber", back_populates="messages")
    conversation = relationship("AIConversation", backref="sms_messages")
    tenant = relationship("Tenant", backref="sms_messages")
    unit = relationship("Unit", backref="sms_messages")

    __table_args__ = (
        CheckConstraint("direction IN ('incoming', 'outgoing')", name='valid_sms_direction'),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='valid_sms_priority'),
        Index('idx_sms_messages_number', 'sms_number_id'),
        Index('idx_sms_messages_conversation', 'conversation_id'),
        Index('idx_sms_messages_direction', 'direction'),
        Index('idx_sms_messages_received', 'received_at'),
        Index('idx_sms_messages_tenant', 'tenant_id'),
    )


class SMSConversation(Base):
    __tablename__ = "sms_conversations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    sms_number_id = Column(GUID, ForeignKey('sms_numbers.id', ondelete='CASCADE'), nullable=False)
    contact_number = Column(String(20), nullable=False)
    contact_name = Column(String(255))

    # Classification
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))
    contractor_id = Column(GUID, ForeignKey('service_contractors.id', ondelete='SET NULL'))

    # Status
    status = Column(String(50), default='active')
    message_count = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)

    # Timestamps
    first_message_at = Column(DateTime(timezone=True))
    last_message_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Metadata
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sms_number = relationship("SMSNumber", back_populates="conversations")
    tenant = relationship("Tenant", backref="sms_conversations")
    unit = relationship("Unit", backref="sms_conversations")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'resolved', 'escalated', 'blocked')",
            name='valid_sms_conversation_status'
        ),
        UniqueConstraint('sms_number_id', 'contact_number', name='unique_sms_conversation'),
        Index('idx_sms_conversations_number', 'sms_number_id'),
        Index('idx_sms_conversations_contact', 'contact_number'),
    )


# ============================================================================
# UNIFIED COMMUNICATION & TEMPLATES
# ============================================================================

class CommunicationLog(Base):
    __tablename__ = "communication_log"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Source
    channel = Column(String(50), nullable=False)
    email_message_id = Column(GUID, ForeignKey('email_messages.id', ondelete='CASCADE'))
    sms_message_id = Column(GUID, ForeignKey('sms_messages.id', ondelete='CASCADE'))
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='SET NULL'))

    # Participants
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='SET NULL'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))
    contractor_id = Column(GUID, ForeignKey('service_contractors.id', ondelete='SET NULL'))

    # Content Summary
    subject_summary = Column(Text)
    content_snippet = Column(Text)

    # Classification
    communication_type = Column(String(100))
    priority = Column(String(50), default='normal')
    sentiment = Column(String(50))

    # AI Processing
    ai_handled = Column(Boolean, default=False)
    ai_confidence = Column(Numeric(5, 4))
    human_escalation = Column(Boolean, default=False)

    # Actions
    action_taken = Column(String(255))
    action_result = Column(JSONB)

    # Timestamps
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    email_message = relationship("EmailMessage", backref="communication_log")
    sms_message = relationship("SMSMessage", backref="communication_log")
    tenant = relationship("Tenant", backref="communication_logs")
    unit = relationship("Unit", backref="communication_logs")

    __table_args__ = (
        CheckConstraint(
            "channel IN ('web', 'email', 'sms', 'phone', 'mobile_app')",
            name='valid_comm_channel'
        ),
        Index('idx_comm_log_channel', 'channel'),
        Index('idx_comm_log_tenant', 'tenant_id'),
        Index('idx_comm_log_occurred', 'occurred_at'),
    )


class ResponseTemplate(Base):
    __tablename__ = "response_templates"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), nullable=False)
    template_category = Column(String(100), nullable=False)

    # Trigger Conditions
    intent_matches = Column(Text)  # JSON array
    keyword_triggers = Column(Text)  # JSON array
    priority_level = Column(String(50))

    # Template Content
    email_subject_template = Column(Text)
    email_body_template = Column(Text)
    sms_template = Column(Text)

    # Configuration
    is_active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    auto_send_confidence_threshold = Column(Numeric(3, 2), default=0.85)

    # Usage Tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    success_rate = Column(Numeric(5, 4))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_templates_category', 'template_category'),
        Index('idx_templates_active', 'is_active'),
    )


class AgentPerformanceMetrics(Base):
    __tablename__ = "agent_performance_metrics"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    metric_date = Column(Date, nullable=False)
    channel = Column(String(50), nullable=False)

    # Volume
    total_messages_received = Column(Integer, default=0)
    total_messages_sent = Column(Integer, default=0)
    total_auto_replies = Column(Integer, default=0)
    total_human_escalations = Column(Integer, default=0)

    # Performance
    avg_response_time_seconds = Column(Integer)
    avg_confidence_score = Column(Numeric(5, 4))
    auto_reply_success_rate = Column(Numeric(5, 4))

    # Intent Distribution
    intent_breakdown = Column(JSONB)

    # Actions
    work_orders_created = Column(Integer, default=0)
    payment_links_sent = Column(Integer, default=0)
    guest_codes_generated = Column(Integer, default=0)

    # Quality
    positive_sentiment_count = Column(Integer, default=0)
    negative_sentiment_count = Column(Integer, default=0)
    spam_caught = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('metric_date', 'channel', name='unique_daily_metric'),
    )
