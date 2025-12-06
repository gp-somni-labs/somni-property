"""Add AI assistant tables

Revision ID: 007_add_ai_assistant
Revises: 006_add_component_sync
Create Date: 2025-11-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '007_add_ai_assistant'
down_revision = '006_add_component_sync'
branch_labels = None
depends_on = None


def upgrade():
    # AI Conversations table
    op.create_table(
        'ai_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE')),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id', ondelete='SET NULL')),
        sa.Column('conversation_type', sa.String(50), server_default='general'),
        sa.Column('channel', sa.String(20), server_default='web'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('user_type', sa.String(20), server_default='tenant'),
        sa.Column('escalated_to_human', sa.String(255)),
        sa.Column('escalation_reason', sa.Text()),
        sa.Column('satisfaction_rating', sa.Integer()),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
    )

    # AI Messages table
    op.create_table(
        'ai_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(100)),
        sa.Column('confidence_score', sa.Numeric(3, 2)),
        sa.Column('actions_taken', postgresql.JSONB),
        sa.Column('message_timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # AI Training Feedback table
    op.create_table(
        'ai_training_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_messages.id', ondelete='CASCADE')),
        sa.Column('feedback_type', sa.String(20)),
        sa.Column('feedback_text', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Indexes for AI Conversations
    op.create_index('idx_ai_conversations_tenant_id', 'ai_conversations', ['tenant_id'])
    op.create_index('idx_ai_conversations_status', 'ai_conversations', ['status'])
    op.create_index('idx_ai_conversations_started_at', 'ai_conversations', ['started_at'])

    # Indexes for AI Messages
    op.create_index('idx_ai_messages_conversation_id', 'ai_messages', ['conversation_id'])
    op.create_index('idx_ai_messages_timestamp', 'ai_messages', ['message_timestamp'])

    # Indexes for AI Training Feedback
    op.create_index('idx_ai_feedback_conversation_id', 'ai_training_feedback', ['conversation_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_ai_feedback_conversation_id', 'ai_training_feedback')
    op.drop_table('ai_training_feedback')

    op.drop_index('idx_ai_messages_timestamp', 'ai_messages')
    op.drop_index('idx_ai_messages_conversation_id', 'ai_messages')
    op.drop_table('ai_messages')

    op.drop_index('idx_ai_conversations_started_at', 'ai_conversations')
    op.drop_index('idx_ai_conversations_status', 'ai_conversations')
    op.drop_index('idx_ai_conversations_tenant_id', 'ai_conversations')
    op.drop_table('ai_conversations')
