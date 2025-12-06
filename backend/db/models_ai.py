"""
AI Assistant Models
Conversation and message tracking for AI chat
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID, JSONB
from db.models import Base


# ============================================================================
# AI ASSISTANT TABLES
# ============================================================================

class AIConversation(Base):
    """AI assistant conversation tracking"""
    __tablename__ = "ai_conversations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID, ForeignKey('tenants.id', ondelete='CASCADE'))
    unit_id = Column(GUID, ForeignKey('units.id', ondelete='SET NULL'))

    # Conversation metadata
    conversation_type = Column(String(50), default='general')  # general, maintenance, rent, lease
    channel = Column(String(20), default='web')  # web, sms, voice
    status = Column(String(20), default='active')  # active, completed, escalated
    user_type = Column(String(20), default='tenant')  # tenant, manager, admin

    # Escalation
    escalated_to_human = Column(String(255))  # Staff member if escalated
    escalation_reason = Column(Text)

    # Satisfaction
    satisfaction_rating = Column(Integer)  # 1-5

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))

    # Relationships
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_ai_conversations_tenant_id', 'tenant_id'),
        Index('idx_ai_conversations_status', 'status'),
        Index('idx_ai_conversations_started_at', 'started_at'),
    )


class AIMessage(Base):
    """Individual messages in AI conversations"""
    __tablename__ = "ai_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False)

    # Message content
    sender_type = Column(String(20), nullable=False)  # user, ai, system
    message_text = Column(Text, nullable=False)

    # AI Intent detection
    intent = Column(String(100))  # maintenance_request, rent_payment, etc.
    confidence_score = Column(Numeric(3, 2))  # 0.00-1.00

    # AI Actions
    actions_taken = Column(JSONB)  # Actions performed by AI

    # Timing
    message_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")

    __table_args__ = (
        Index('idx_ai_messages_conversation_id', 'conversation_id'),
        Index('idx_ai_messages_timestamp', 'message_timestamp'),
    )


class AITrainingFeedback(Base):
    """User feedback on AI responses for training"""
    __tablename__ = "ai_training_feedback"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID, ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(GUID, ForeignKey('ai_messages.id', ondelete='CASCADE'))

    # Feedback
    feedback_type = Column(String(20))  # helpful, not_helpful, incorrect
    feedback_text = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_ai_feedback_conversation_id', 'conversation_id'),
    )
