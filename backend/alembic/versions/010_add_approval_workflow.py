"""010_add_approval_workflow

Revision ID: 010_add_approval_workflow
Revises: 009_add_staff_contractors
Create Date: 2025-11-16 10:30:00.000000

Add approval workflow tables for human-in-the-middle approval system
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_approval_workflow'
down_revision = '009_add_staff_contractors'
branch_labels = None
depends_on = None


def upgrade():
    """Add approval workflow tables"""

    # ========================================================================
    # PENDING ACTIONS TABLE
    # ========================================================================
    op.create_table(
        'pending_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Source
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_message_id', postgresql.UUID(as_uuid=True)),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='SET NULL')),

        # Requester
        sa.Column('requester_type', sa.String(50), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('contractor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contractors.id', ondelete='SET NULL')),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id', ondelete='SET NULL')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL')),
        sa.Column('requester_name', sa.String(255)),
        sa.Column('requester_contact', sa.String(255)),

        # Action Details
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('action_category', sa.String(50), nullable=False),
        sa.Column('action_title', sa.Text(), nullable=False),
        sa.Column('action_description', sa.Text(), nullable=False),
        sa.Column('action_data', postgresql.JSONB(), nullable=False),

        # AI Analysis
        sa.Column('ai_intent', sa.String(100)),
        sa.Column('ai_confidence', sa.Numeric(5, 4)),
        sa.Column('ai_suggested_action', sa.Text()),
        sa.Column('ai_risk_assessment', sa.String(50)),
        sa.Column('ai_reasoning', sa.Text()),

        # Urgency & Priority
        sa.Column('urgency', sa.String(50), server_default='normal'),
        sa.Column('priority', sa.Integer(), server_default='3'),
        sa.Column('estimated_cost', sa.Numeric(10, 2)),

        # Approval Status
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('requires_multi_approval', sa.Boolean(), server_default='false'),
        sa.Column('approval_count_required', sa.Integer(), server_default='1'),
        sa.Column('approval_count_current', sa.Integer(), server_default='0'),

        # Auto-Approval
        sa.Column('can_auto_approve', sa.Boolean(), server_default='false'),
        sa.Column('auto_approve_reason', sa.String(255)),
        sa.Column('auto_approved_at', sa.DateTime(timezone=True)),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),

        # Approval/Rejection
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('rejected_at', sa.DateTime(timezone=True)),
        sa.Column('rejection_reason', sa.Text()),

        # Execution
        sa.Column('executed', sa.Boolean(), server_default='false'),
        sa.Column('executed_at', sa.DateTime(timezone=True)),
        sa.Column('execution_result', postgresql.JSONB()),
        sa.Column('execution_error', sa.Text()),

        # Notification Tracking
        sa.Column('notification_sent', sa.Boolean(), server_default='false'),
        sa.Column('notification_sent_at', sa.DateTime(timezone=True)),
        sa.Column('reminder_sent_count', sa.Integer(), server_default='0'),
        sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True)),

        # Metadata
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('notes', sa.Text())
    )

    # Pending actions check constraints
    op.create_check_constraint(
        'valid_source_type',
        'pending_actions',
        "source_type IN ('email', 'sms', 'web', 'api')"
    )

    op.create_check_constraint(
        'valid_requester_type',
        'pending_actions',
        "requester_type IN ('tenant', 'contractor', 'landlord', 'client', 'system')"
    )

    op.create_check_constraint(
        'valid_urgency',
        'pending_actions',
        "urgency IN ('low', 'normal', 'high', 'critical', 'emergency')"
    )

    op.create_check_constraint(
        'valid_action_status',
        'pending_actions',
        "status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')"
    )

    # Pending actions indexes
    op.create_index('idx_pending_actions_status', 'pending_actions', ['status'])
    op.create_index('idx_pending_actions_action_type', 'pending_actions', ['action_type'])
    op.create_index('idx_pending_actions_urgency', 'pending_actions', ['urgency'])
    op.create_index('idx_pending_actions_created', 'pending_actions', ['created_at'])
    op.create_index('idx_pending_actions_property', 'pending_actions', ['property_id'])

    # ========================================================================
    # APPROVAL ACTIONS TABLE
    # ========================================================================
    op.create_table(
        'approval_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pending_action_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pending_actions.id', ondelete='CASCADE'), nullable=False),

        # Approver
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('approver_name', sa.String(255)),
        sa.Column('approver_role', sa.String(100)),

        # Decision
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('decision_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Reasoning
        sa.Column('reason', sa.Text()),
        sa.Column('conditions', sa.Text()),
        sa.Column('modifications', postgresql.JSONB()),

        # Delegation
        sa.Column('delegated_to', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('delegated_at', sa.DateTime(timezone=True)),

        # Notification
        sa.Column('notification_method', sa.String(50)),
        sa.Column('response_time_seconds', sa.Integer()),

        # Metadata
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )

    # Approval actions check constraints
    op.create_check_constraint(
        'valid_decision',
        'approval_actions',
        "decision IN ('approve', 'reject', 'request_info', 'delegate')"
    )

    # Approval actions indexes
    op.create_index('idx_approval_actions_pending', 'approval_actions', ['pending_action_id'])
    op.create_index('idx_approval_actions_approver', 'approval_actions', ['approver_id'])
    op.create_index('idx_approval_actions_decision', 'approval_actions', ['decision'])

    # ========================================================================
    # APPROVAL POLICIES TABLE
    # ========================================================================
    op.create_table(
        'approval_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_name', sa.String(255), nullable=False, unique=True),
        sa.Column('policy_description', sa.Text()),

        # Scope
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE')),
        sa.Column('applies_to_all_properties', sa.Boolean(), server_default='false'),

        # Conditions
        sa.Column('action_types', sa.Text(), nullable=False),  # JSON array as text
        sa.Column('requester_types', sa.Text()),  # JSON array as text
        sa.Column('urgency_levels', sa.Text()),  # JSON array as text
        sa.Column('max_estimated_cost', sa.Numeric(10, 2)),

        # Auto-Approval Logic
        sa.Column('auto_approve_enabled', sa.Boolean(), server_default='false'),
        sa.Column('auto_approve_conditions', postgresql.JSONB()),

        # Approval Requirements
        sa.Column('requires_approval', sa.Boolean(), server_default='true'),
        sa.Column('requires_multi_approval', sa.Boolean(), server_default='false'),
        sa.Column('approval_count_required', sa.Integer(), server_default='1'),
        sa.Column('approved_roles', sa.Text()),  # JSON array as text

        # Time Limits
        sa.Column('approval_timeout_hours', sa.Integer()),
        sa.Column('business_hours_only', sa.Boolean(), server_default='false'),

        # Notification Settings
        sa.Column('notify_on_creation', sa.Boolean(), server_default='true'),
        sa.Column('notify_on_approval', sa.Boolean(), server_default='true'),
        sa.Column('notify_on_rejection', sa.Boolean(), server_default='true'),
        sa.Column('escalation_after_hours', sa.Integer()),

        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('priority', sa.Integer(), server_default='100'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'))
    )

    # Approval policies indexes
    op.create_index('idx_approval_policies_active', 'approval_policies', ['is_active'])
    op.create_index('idx_approval_policies_priority', 'approval_policies', ['priority'])
    op.create_index('idx_approval_policies_property', 'approval_policies', ['property_id'])

    # ========================================================================
    # APPROVAL NOTIFICATIONS TABLE
    # ========================================================================
    op.create_table(
        'approval_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pending_action_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pending_actions.id', ondelete='CASCADE'), nullable=False),

        # Notification Details
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('notification_channel', sa.String(50), nullable=False),

        # Recipients
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('recipient_contact', sa.String(255)),

        # Content
        sa.Column('notification_title', sa.Text()),
        sa.Column('notification_body', sa.Text()),
        sa.Column('notification_data', postgresql.JSONB()),

        # Delivery Status
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('delivered', sa.Boolean(), server_default='false'),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('read', sa.Boolean(), server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.Column('clicked', sa.Boolean(), server_default='false'),
        sa.Column('clicked_at', sa.DateTime(timezone=True)),

        # Provider Details
        sa.Column('provider_message_id', sa.String(500)),
        sa.Column('provider_status', sa.String(100)),
        sa.Column('provider_error', sa.Text()),

        # Metadata
        sa.Column('metadata', postgresql.JSONB())
    )

    # Approval notifications check constraints
    op.create_check_constraint(
        'valid_notification_type',
        'approval_notifications',
        "notification_type IN ('creation', 'reminder', 'approval', 'rejection', 'execution', 'expiration')"
    )

    op.create_check_constraint(
        'valid_notification_channel',
        'approval_notifications',
        "notification_channel IN ('gotify', 'ntfy', 'email', 'sms')"
    )

    # Approval notifications indexes
    op.create_index('idx_approval_notifications_pending', 'approval_notifications', ['pending_action_id'])
    op.create_index('idx_approval_notifications_channel', 'approval_notifications', ['notification_channel'])
    op.create_index('idx_approval_notifications_type', 'approval_notifications', ['notification_type'])
    op.create_index('idx_approval_notifications_recipient', 'approval_notifications', ['recipient_id'])


def downgrade():
    """Remove approval workflow tables"""

    # Drop approval_notifications table
    op.drop_index('idx_approval_notifications_recipient', table_name='approval_notifications')
    op.drop_index('idx_approval_notifications_type', table_name='approval_notifications')
    op.drop_index('idx_approval_notifications_channel', table_name='approval_notifications')
    op.drop_index('idx_approval_notifications_pending', table_name='approval_notifications')
    op.drop_constraint('valid_notification_channel', 'approval_notifications', type_='check')
    op.drop_constraint('valid_notification_type', 'approval_notifications', type_='check')
    op.drop_table('approval_notifications')

    # Drop approval_policies table
    op.drop_index('idx_approval_policies_property', table_name='approval_policies')
    op.drop_index('idx_approval_policies_priority', table_name='approval_policies')
    op.drop_index('idx_approval_policies_active', table_name='approval_policies')
    op.drop_table('approval_policies')

    # Drop approval_actions table
    op.drop_index('idx_approval_actions_decision', table_name='approval_actions')
    op.drop_index('idx_approval_actions_approver', table_name='approval_actions')
    op.drop_index('idx_approval_actions_pending', table_name='approval_actions')
    op.drop_constraint('valid_decision', 'approval_actions', type_='check')
    op.drop_table('approval_actions')

    # Drop pending_actions table
    op.drop_index('idx_pending_actions_property', table_name='pending_actions')
    op.drop_index('idx_pending_actions_created', table_name='pending_actions')
    op.drop_index('idx_pending_actions_urgency', table_name='pending_actions')
    op.drop_index('idx_pending_actions_action_type', table_name='pending_actions')
    op.drop_index('idx_pending_actions_status', table_name='pending_actions')
    op.drop_constraint('valid_action_status', 'pending_actions', type_='check')
    op.drop_constraint('valid_urgency', 'pending_actions', type_='check')
    op.drop_constraint('valid_requester_type', 'pending_actions', type_='check')
    op.drop_constraint('valid_source_type', 'pending_actions', type_='check')
    op.drop_table('pending_actions')
