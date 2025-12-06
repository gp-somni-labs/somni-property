"""Add Family Mode tables for MSP features

Revision ID: 025_add_family_mode_tables
Revises: 024_add_quote_visual_assets
Create Date: 2025-11-21 05:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '025_add_family_mode_tables'
down_revision = '024_add_quote_visual_assets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE subscriptiontier AS ENUM ('starter', 'pro', 'enterprise');
        CREATE TYPE subscriptionstatus AS ENUM ('active', 'cancelled', 'past_due', 'suspended');
        CREATE TYPE ticketpriority AS ENUM ('low', 'medium', 'high', 'critical');
        CREATE TYPE ticketstatus AS ENUM ('open', 'in_progress', 'waiting_customer', 'resolved', 'closed');
        CREATE TYPE alertseverity AS ENUM ('info', 'warning', 'critical');
        CREATE TYPE alertstatus AS ENUM ('active', 'acknowledged', 'resolved', 'dismissed');
    """)

    # Family Subscriptions table
    op.create_table(
        'family_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('tier', sa.Enum('starter', 'pro', 'enterprise', name='subscriptiontier'), nullable=False, server_default='starter'),
        sa.Column('status', sa.Enum('active', 'cancelled', 'past_due', 'suspended', name='subscriptionstatus'), nullable=False, server_default='active'),
        sa.Column('base_price', sa.Float(), nullable=False),
        sa.Column('included_support_hours', sa.Integer(), nullable=False),
        sa.Column('overage_rate', sa.Float(), nullable=False),
        sa.Column('billing_cycle_start', sa.DateTime(), nullable=False),
        sa.Column('next_billing_date', sa.DateTime(), nullable=False),
        sa.Column('auto_renew', sa.Boolean(), server_default='true'),
        sa.Column('addons', postgresql.JSONB(), server_default='{}'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Support Hours table
    op.create_table(
        'support_hours',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_subscriptions.id'), nullable=False),
        sa.Column('billing_cycle_start', sa.DateTime(), nullable=False),
        sa.Column('billing_cycle_end', sa.DateTime(), nullable=False),
        sa.Column('included_hours', sa.Integer(), nullable=False),
        sa.Column('used_hours', sa.Float(), server_default='0.0'),
        sa.Column('overage_hours', sa.Float(), server_default='0.0'),
        sa.Column('base_cost', sa.Float(), server_default='0.0'),
        sa.Column('overage_cost', sa.Float(), server_default='0.0'),
        sa.Column('total_cost', sa.Float(), server_default='0.0'),
        sa.Column('support_sessions', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Support Sessions table
    op.create_table(
        'support_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_subscriptions.id'), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('support_tickets.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('support_engineer', sa.String(255)),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('duration_hours', sa.Float(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=False),
        sa.Column('billable', sa.Boolean(), server_default='true'),
        sa.Column('hourly_rate', sa.Float()),
        sa.Column('total_cost', sa.Float()),
        sa.Column('notes', sa.Text()),
        sa.Column('work_performed', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Family Support Tickets table
    op.create_table(
        'family_support_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_subscriptions.id'), nullable=False),
        sa.Column('ticket_number', sa.String(50), unique=True, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'critical', name='ticketpriority'), nullable=False, server_default='medium'),
        sa.Column('status', sa.Enum('open', 'in_progress', 'waiting_customer', 'resolved', 'closed', name='ticketstatus'), nullable=False, server_default='open'),
        sa.Column('category', sa.String(100)),
        sa.Column('assigned_to', sa.String(255)),
        sa.Column('assigned_at', sa.DateTime()),
        sa.Column('first_response_at', sa.DateTime()),
        sa.Column('resolved_at', sa.DateTime()),
        sa.Column('closed_at', sa.DateTime()),
        sa.Column('sla_response_time_hours', sa.Integer()),
        sa.Column('sla_resolution_time_hours', sa.Integer()),
        sa.Column('sla_response_breached', sa.Boolean(), server_default='false'),
        sa.Column('sla_resolution_breached', sa.Boolean(), server_default='false'),
        sa.Column('customer_name', sa.String(255)),
        sa.Column('customer_email', sa.String(255)),
        sa.Column('customer_phone', sa.String(50)),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('smart_devices.id'), nullable=True),
        sa.Column('hub_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id'), nullable=True),
        sa.Column('error_logs', sa.Text()),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('attachments', postgresql.JSONB(), server_default='[]'),
        sa.Column('internal_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Ticket Comments table
    op.create_table(
        'ticket_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_support_tickets.id'), nullable=False),
        sa.Column('author_name', sa.String(255), nullable=False),
        sa.Column('author_email', sa.String(255), nullable=False),
        sa.Column('author_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Family Alerts table
    op.create_table(
        'family_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_subscriptions.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('info', 'warning', 'critical', name='alertseverity'), nullable=False, server_default='info'),
        sa.Column('status', sa.Enum('active', 'acknowledged', 'resolved', 'dismissed', name='alertstatus'), nullable=False, server_default='active'),
        sa.Column('source_type', sa.String(100)),
        sa.Column('source_id', sa.String(255)),
        sa.Column('source_name', sa.String(255)),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('smart_devices.id'), nullable=True),
        sa.Column('hub_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime()),
        sa.Column('acknowledged_by', sa.String(255)),
        sa.Column('resolved_at', sa.DateTime()),
        sa.Column('resolved_by', sa.String(255)),
        sa.Column('resolution_notes', sa.Text()),
        sa.Column('escalated', sa.Boolean(), server_default='false'),
        sa.Column('escalated_to_ticket', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_support_tickets.id'), nullable=True),
        sa.Column('escalated_at', sa.DateTime()),
        sa.Column('notifications_sent', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Family Billing table
    op.create_table(
        'family_billing',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_subscriptions.id'), nullable=False),
        sa.Column('billing_period_start', sa.DateTime(), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(), nullable=False),
        sa.Column('invoice_date', sa.DateTime(), nullable=False),
        sa.Column('billing_date', sa.DateTime(), nullable=False),  # Add alias for analytics compatibility
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('base_subscription', sa.Float(), nullable=False),
        sa.Column('addons_total', sa.Float(), server_default='0.0'),
        sa.Column('support_hours_base', sa.Float(), server_default='0.0'),
        sa.Column('support_hours_overage', sa.Float(), server_default='0.0'),
        sa.Column('custom_services', sa.Float(), server_default='0.0'),
        sa.Column('hardware_charges', sa.Float(), server_default='0.0'),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.Column('tax', sa.Float(), server_default='0.0'),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('amount_due', sa.Float(), nullable=False),  # Add alias for analytics compatibility
        sa.Column('paid', sa.Boolean(), server_default='false'),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('payment_method', sa.String(100)),
        sa.Column('transaction_id', sa.String(255)),
        sa.Column('line_items', postgresql.JSONB(), server_default='[]'),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Automation Templates table
    op.create_table(
        'automation_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100)),
        sa.Column('required_devices', postgresql.JSONB(), server_default='[]'),
        sa.Column('tier_requirement', sa.Enum('starter', 'pro', 'enterprise', name='subscriptiontier'), server_default='starter'),
        sa.Column('is_premium', sa.Boolean(), server_default='false'),
        sa.Column('setup_fee', sa.Float(), server_default='0.0'),
        sa.Column('monthly_fee', sa.Float(), server_default='0.0'),
        sa.Column('ha_automation_yaml', sa.Text()),
        sa.Column('configuration_schema', postgresql.JSONB()),
        sa.Column('icon', sa.String(100)),
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('popularity_score', sa.Integer(), server_default='0'),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Create indexes
    op.create_index('ix_family_subscriptions_client_id', 'family_subscriptions', ['client_id'])
    op.create_index('ix_family_subscriptions_status', 'family_subscriptions', ['status'])
    op.create_index('ix_support_hours_subscription_id', 'support_hours', ['subscription_id'])
    op.create_index('ix_family_support_tickets_subscription_id', 'family_support_tickets', ['subscription_id'])
    op.create_index('ix_family_support_tickets_status', 'family_support_tickets', ['status'])
    op.create_index('ix_family_billing_subscription_id', 'family_billing', ['subscription_id'])
    op.create_index('ix_family_billing_paid', 'family_billing', ['paid'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('automation_templates')
    op.drop_table('family_billing')
    op.drop_table('family_alerts')
    op.drop_table('ticket_comments')
    op.drop_table('family_support_tickets')
    op.drop_table('support_sessions')
    op.drop_table('support_hours')
    op.drop_table('family_subscriptions')

    # Drop enum types
    op.execute('DROP TYPE alertstatus')
    op.execute('DROP TYPE alertseverity')
    op.execute('DROP TYPE ticketstatus')
    op.execute('DROP TYPE ticketpriority')
    op.execute('DROP TYPE subscriptionstatus')
    op.execute('DROP TYPE subscriptiontier')
