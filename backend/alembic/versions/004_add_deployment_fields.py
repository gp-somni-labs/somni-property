"""004_add_deployment_fields

Revision ID: 004_add_deployment_fields
Revises: 003_tier_0_standalone
Create Date: 2025-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_deployment_fields'
down_revision = '003_tier_0_standalone'
branch_labels = None
depends_on = None


def upgrade():
    """Add automatic deployment tracking fields to property_edge_nodes table"""

    # Add deployment status tracking fields
    op.add_column('property_edge_nodes', sa.Column('deployment_status', sa.String(30), server_default='pending'))
    op.add_column('property_edge_nodes', sa.Column('deployment_started_at', sa.DateTime(timezone=True)))
    op.add_column('property_edge_nodes', sa.Column('deployment_completed_at', sa.DateTime(timezone=True)))
    op.add_column('property_edge_nodes', sa.Column('deployment_error_message', sa.Text()))
    op.add_column('property_edge_nodes', sa.Column('deployment_progress_percent', sa.Integer(), server_default='0'))
    op.add_column('property_edge_nodes', sa.Column('deployment_current_step', sa.String(255)))

    # Add SSH configuration fields (for Tier 2/3 k3s deployment)
    op.add_column('property_edge_nodes', sa.Column('deployment_ssh_host', sa.String(255)))
    op.add_column('property_edge_nodes', sa.Column('deployment_ssh_port', sa.Integer(), server_default='22'))
    op.add_column('property_edge_nodes', sa.Column('deployment_ssh_user', sa.String(100)))
    op.add_column('property_edge_nodes', sa.Column('deployment_ssh_key_encrypted', sa.Text()))

    # Add Home Assistant configuration fields (for Tier 0 component deployment)
    op.add_column('property_edge_nodes', sa.Column('deployment_ha_url', sa.String(500)))
    op.add_column('property_edge_nodes', sa.Column('deployment_ha_token_hash', sa.String(500)))

    # Add deployment details fields
    op.add_column('property_edge_nodes', sa.Column('deployed_components', postgresql.JSONB(), nullable=True))
    op.add_column('property_edge_nodes', sa.Column('deployment_logs', sa.Text()))
    op.add_column('property_edge_nodes', sa.Column('deployment_manifest_version', sa.String(100)))

    # Add check constraint for deployment_status
    op.create_check_constraint(
        'valid_deployment_status',
        'property_edge_nodes',
        "deployment_status IN ('pending', 'in_progress', 'deployed', 'failed', 'unknown')"
    )


def downgrade():
    """Remove deployment tracking fields"""

    # Drop check constraint
    op.drop_constraint('valid_deployment_status', 'property_edge_nodes', type_='check')

    # Drop columns
    op.drop_column('property_edge_nodes', 'deployment_manifest_version')
    op.drop_column('property_edge_nodes', 'deployment_logs')
    op.drop_column('property_edge_nodes', 'deployed_components')
    op.drop_column('property_edge_nodes', 'deployment_ha_token_hash')
    op.drop_column('property_edge_nodes', 'deployment_ha_url')
    op.drop_column('property_edge_nodes', 'deployment_ssh_key_encrypted')
    op.drop_column('property_edge_nodes', 'deployment_ssh_user')
    op.drop_column('property_edge_nodes', 'deployment_ssh_port')
    op.drop_column('property_edge_nodes', 'deployment_ssh_host')
    op.drop_column('property_edge_nodes', 'deployment_current_step')
    op.drop_column('property_edge_nodes', 'deployment_progress_percent')
    op.drop_column('property_edge_nodes', 'deployment_error_message')
    op.drop_column('property_edge_nodes', 'deployment_completed_at')
    op.drop_column('property_edge_nodes', 'deployment_started_at')
    op.drop_column('property_edge_nodes', 'deployment_status')
