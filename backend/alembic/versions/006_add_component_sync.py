"""Add component sync table

Revision ID: 006
Revises: 005
Create Date: 2025-11-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_component_sync'
down_revision = '005_add_clients'
branch_labels = None
depends_on = None


def upgrade():
    """Add component_syncs table for tracking component sync operations."""
    op.create_table(
        'component_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_hub_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_hub_host', sa.String(length=255), nullable=False),
        sa.Column('target_hub_type', sa.String(length=30), nullable=False),
        sa.Column('sync_method', sa.String(length=20), server_default='rsync', nullable=True),
        sa.Column('sync_started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sync_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(length=20), server_default='in_progress', nullable=True),
        sa.Column('components_requested', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('components_synced', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('addons_requested', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('addons_synced', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sync_logs', sa.Text(), nullable=True),
        sa.Column('error_messages', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('gitops_repo_url', sa.String(length=500), nullable=True),
        sa.Column('gitops_commit_sha', sa.String(length=255), nullable=True),
        sa.Column('gitops_branch', sa.String(length=255), nullable=True),
        sa.Column('ha_restart_initiated', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('ha_restart_successful', sa.Boolean(), nullable=True),
        sa.Column('initiated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['target_hub_id'], ['property_edge_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "sync_status IN ('in_progress', 'success', 'partial_success', 'failed')",
            name='valid_component_sync_status'
        ),
        sa.CheckConstraint(
            "target_hub_type IN ('tier_0_standalone', 'tier_2_property', 'tier_3_residential')",
            name='valid_component_sync_hub_type'
        ),
        sa.CheckConstraint(
            "sync_method IN ('rsync', 'gitops')",
            name='valid_sync_method'
        ),
    )

    # Create indexes
    op.create_index('idx_component_syncs_target_hub_id', 'component_syncs', ['target_hub_id'])
    op.create_index('idx_component_syncs_sync_started_at', 'component_syncs', ['sync_started_at'])
    op.create_index('idx_component_syncs_sync_status', 'component_syncs', ['sync_status'])
    op.create_index('idx_component_syncs_target_hub_type', 'component_syncs', ['target_hub_type'])
    op.create_index('idx_component_syncs_sync_method', 'component_syncs', ['sync_method'])


def downgrade():
    """Remove component_syncs table."""
    op.drop_index('idx_component_syncs_sync_method', table_name='component_syncs')
    op.drop_index('idx_component_syncs_target_hub_type', table_name='component_syncs')
    op.drop_index('idx_component_syncs_sync_status', table_name='component_syncs')
    op.drop_index('idx_component_syncs_sync_started_at', table_name='component_syncs')
    op.drop_index('idx_component_syncs_target_hub_id', table_name='component_syncs')
    op.drop_table('component_syncs')
