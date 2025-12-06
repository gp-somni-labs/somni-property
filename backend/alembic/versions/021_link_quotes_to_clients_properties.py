"""Link quotes to clients and properties

Revision ID: 021_link_quotes_to_clients_properties
Revises: 020_add_project_phases
Create Date: 2025-11-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021_link_quotes_to_clients_properties'
down_revision = '020_add_project_phases'
branch_labels = None
depends_on = None


def upgrade():
    # Add client and property relationships to quotes table
    op.add_column('quotes', sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='SET NULL')))
    op.add_column('quotes', sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL')))
    op.add_column('quotes', sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='SET NULL')))

    # Create indexes for new foreign keys
    op.create_index('idx_quotes_client_id', 'quotes', ['client_id'])
    op.create_index('idx_quotes_property_id', 'quotes', ['property_id'])
    op.create_index('idx_quotes_building_id', 'quotes', ['building_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_quotes_building_id', 'quotes')
    op.drop_index('idx_quotes_property_id', 'quotes')
    op.drop_index('idx_quotes_client_id', 'quotes')

    # Drop columns
    op.drop_column('quotes', 'building_id')
    op.drop_column('quotes', 'property_id')
    op.drop_column('quotes', 'client_id')
