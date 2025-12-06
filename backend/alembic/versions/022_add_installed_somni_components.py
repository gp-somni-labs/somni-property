"""Add installed Somni components tracking to property edge nodes

Revision ID: 022_add_installed_somni_components
Revises: 021_link_quotes_to_clients_properties
Create Date: 2025-11-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '022_add_installed_somni_components'
down_revision = '021_link_quotes_to_clients_properties'
branch_labels = None
depends_on = None


def upgrade():
    # Add installed_somni_components field to track which Somni HA custom components are installed
    op.add_column('property_edge_nodes',
        sa.Column('installed_somni_components', postgresql.JSONB, server_default='{}'))

    # Add last component sync tracking
    op.add_column('property_edge_nodes',
        sa.Column('last_component_sync_id', postgresql.UUID(as_uuid=True),
                 sa.ForeignKey('component_syncs.id', ondelete='SET NULL')))

    op.add_column('property_edge_nodes',
        sa.Column('last_component_sync_at', sa.DateTime(timezone=True)))

    # Create index for last_component_sync_id
    op.create_index('idx_property_edge_nodes_last_component_sync_id',
                   'property_edge_nodes', ['last_component_sync_id'])


def downgrade():
    # Drop index
    op.drop_index('idx_property_edge_nodes_last_component_sync_id', 'property_edge_nodes')

    # Drop columns
    op.drop_column('property_edge_nodes', 'last_component_sync_at')
    op.drop_column('property_edge_nodes', 'last_component_sync_id')
    op.drop_column('property_edge_nodes', 'installed_somni_components')
