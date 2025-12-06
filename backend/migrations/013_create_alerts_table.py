"""
Migration 013: Create alerts table
Creates the alerts table for aggregating Home Assistant and MQTT events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


def upgrade():
    """Create alerts table and indexes"""

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hub_id', UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id'), nullable=True),

        # Alert classification
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),

        # Alert details
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=True),

        # Timestamps
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('acknowledged_by', sa.String(255), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),

        # Status
        sa.Column('status', sa.String(20), default='open'),

        # Additional context
        sa.Column('metadata', JSONB, nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Constraints
        sa.CheckConstraint("severity IN ('info', 'warning', 'critical')", name='valid_alert_severity'),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name='valid_alert_status'),
    )

    # Create indexes
    op.create_index('idx_alerts_hub_id', 'alerts', ['hub_id'])
    op.create_index('idx_alerts_severity', 'alerts', ['severity'])
    op.create_index('idx_alerts_occurred_at', 'alerts', ['occurred_at'])
    op.create_index('idx_alerts_status', 'alerts', ['status'])


def downgrade():
    """Drop alerts table and indexes"""

    # Drop indexes
    op.drop_index('idx_alerts_status', table_name='alerts')
    op.drop_index('idx_alerts_occurred_at', table_name='alerts')
    op.drop_index('idx_alerts_severity', table_name='alerts')
    op.drop_index('idx_alerts_hub_id', table_name='alerts')

    # Drop table
    op.drop_table('alerts')
