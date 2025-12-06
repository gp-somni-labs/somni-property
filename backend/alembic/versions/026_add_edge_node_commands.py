"""Add edge_node_commands table for remote hub control

Revision ID: 026_add_edge_node_commands
Revises: 025_add_family_mode_tables
Create Date: 2025-11-20 23:30:00.000000

This migration adds the edge_node_commands table to support remote control
of edge hubs from the Central Hub. Commands are polled by the
somni_property_sync Home Assistant integration every 60 seconds.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_add_edge_node_commands'
down_revision = '025_add_family_mode_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create edge_node_commands table
    op.create_table(
        'edge_node_commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hub_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id', ondelete='CASCADE'), nullable=False),

        # Command details
        sa.Column('command_type', sa.String(50), nullable=False, comment='service_call, state_change, script, automation'),
        sa.Column('target_entity', sa.String(255), nullable=False, comment='Entity ID (e.g., light.living_room)'),
        sa.Column('action', sa.String(100), nullable=False, comment='turn_on, turn_off, lock, unlock, trigger, etc.'),
        sa.Column('parameters', postgresql.JSONB, server_default='{}', comment='Service parameters (brightness, color, etc.)'),

        # Command metadata
        sa.Column('created_by', sa.String(255), comment='User or system that created command'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Execution tracking
        sa.Column('status', sa.String(20), server_default='pending', nullable=False, comment='pending, executing, success, failed, timeout'),
        sa.Column('executed_at', sa.DateTime(timezone=True)),
        sa.Column('result', postgresql.JSONB, comment='Execution result from hub'),
        sa.Column('error_message', sa.Text),

        # Timeout (commands older than 5 minutes are considered stale)
        sa.Column('timeout_seconds', sa.Integer, server_default='300', nullable=False),
    )

    # Create indexes for performance
    op.create_index('idx_edge_commands_hub_id', 'edge_node_commands', ['hub_id'])
    op.create_index('idx_edge_commands_status', 'edge_node_commands', ['status'])
    op.create_index('idx_edge_commands_created_at', 'edge_node_commands', ['created_at'])

    # Create composite index for polling queries (hub_id + status)
    op.create_index('idx_edge_commands_hub_status', 'edge_node_commands', ['hub_id', 'status'])

    print("✅ Created edge_node_commands table with indexes")
    print("📡 Edge hubs can now receive commands from Central Hub")
    print("🔄 Commands are polled via GET /api/v1/sync/commands every 60 seconds")


def downgrade():
    # Drop indexes
    op.drop_index('idx_edge_commands_hub_status', 'edge_node_commands')
    op.drop_index('idx_edge_commands_created_at', 'edge_node_commands')
    op.drop_index('idx_edge_commands_status', 'edge_node_commands')
    op.drop_index('idx_edge_commands_hub_id', 'edge_node_commands')

    # Drop table
    op.drop_table('edge_node_commands')

    print("🗑️ Dropped edge_node_commands table")
