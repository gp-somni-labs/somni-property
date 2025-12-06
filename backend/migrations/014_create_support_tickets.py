"""
Migration 014: Create support_tickets table
Creates the support_tickets table for proactive outreach workflow (Alerts → Tickets)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


def upgrade():
    """Create support_tickets table and indexes"""

    # Create support_tickets table
    op.create_table(
        'support_tickets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=True),
        sa.Column('hub_id', UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id'), nullable=True),
        sa.Column('alert_id', UUID(as_uuid=True), sa.ForeignKey('alerts.id'), nullable=True),

        # Ticket classification
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),

        # Status tracking
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('priority', sa.String(20), nullable=True),

        # SLA tracking
        sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sla_breach', sa.Boolean(), default=False),

        # Assignment
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),

        # Resolution
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),

        # Client communication
        sa.Column('client_notified', sa.Boolean(), default=False),
        sa.Column('client_notified_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed')", name='valid_ticket_status'),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='valid_ticket_severity'),
    )

    # Create indexes
    op.create_index('idx_support_tickets_client_id', 'support_tickets', ['client_id'])
    op.create_index('idx_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('idx_support_tickets_severity', 'support_tickets', ['severity'])
    op.create_index('idx_support_tickets_sla_due_at', 'support_tickets', ['sla_due_at'])


def downgrade():
    """Drop support_tickets table and indexes"""

    # Drop indexes
    op.drop_index('idx_support_tickets_sla_due_at', table_name='support_tickets')
    op.drop_index('idx_support_tickets_severity', table_name='support_tickets')
    op.drop_index('idx_support_tickets_status', table_name='support_tickets')
    op.drop_index('idx_support_tickets_client_id', table_name='support_tickets')

    # Drop table
    op.drop_table('support_tickets')
