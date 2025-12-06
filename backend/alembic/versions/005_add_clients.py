"""005_add_clients

Revision ID: 005_add_clients
Revises: 004_add_deployment_fields
Create Date: 2025-11-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_clients'
down_revision = '004_add_deployment_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add clients table for Somni Intelligent Living as a Service customer management"""

    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Basic Information
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),

        # Contact Information
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('address_line1', sa.String(255)),
        sa.Column('address_line2', sa.String(255)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(50)),
        sa.Column('zip_code', sa.String(20)),
        sa.Column('country', sa.String(100), server_default='USA'),

        # Billing Information
        sa.Column('subscription_plan', sa.String(100)),
        sa.Column('monthly_fee', sa.Numeric(10, 2)),
        sa.Column('billing_status', sa.String(20), server_default='active'),

        # SLA Information
        sa.Column('support_level', sa.String(50)),
        sa.Column('response_time_hours', sa.Integer()),
        sa.Column('uptime_guarantee', sa.Numeric(5, 2)),

        # Tier 2 Enterprise Specific
        sa.Column('is_landlord_client', sa.Boolean(), server_default='false'),
        sa.Column('rent_collection_fee_percent', sa.Numeric(5, 2)),

        # Relationships to Infrastructure
        sa.Column('edge_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id', ondelete='SET NULL')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL')),

        # Account Status
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('onboarding_completed', sa.Boolean(), server_default='false'),
        sa.Column('onboarded_at', sa.DateTime(timezone=True)),
        sa.Column('churned_at', sa.DateTime(timezone=True)),
        sa.Column('churn_reason', sa.Text()),

        # Notes
        sa.Column('notes', sa.Text()),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add check constraints
    op.create_check_constraint(
        'valid_client_tier',
        'clients',
        "tier IN ('tier_0', 'tier_1', 'tier_2')"
    )

    op.create_check_constraint(
        'valid_billing_status',
        'clients',
        "billing_status IN ('active', 'suspended', 'cancelled', 'past_due')"
    )

    op.create_check_constraint(
        'valid_client_status',
        'clients',
        "status IN ('active', 'suspended', 'cancelled', 'churned')"
    )

    # Add indexes for performance
    op.create_index('idx_clients_tier', 'clients', ['tier'])
    op.create_index('idx_clients_status', 'clients', ['status'])
    op.create_index('idx_clients_billing_status', 'clients', ['billing_status'])
    op.create_index('idx_clients_email', 'clients', ['email'])
    op.create_index('idx_clients_edge_node_id', 'clients', ['edge_node_id'])
    op.create_index('idx_clients_property_id', 'clients', ['property_id'])


def downgrade():
    """Remove clients table"""

    # Drop indexes
    op.drop_index('idx_clients_property_id', table_name='clients')
    op.drop_index('idx_clients_edge_node_id', table_name='clients')
    op.drop_index('idx_clients_email', table_name='clients')
    op.drop_index('idx_clients_billing_status', table_name='clients')
    op.drop_index('idx_clients_status', table_name='clients')
    op.drop_index('idx_clients_tier', table_name='clients')

    # Drop check constraints
    op.drop_constraint('valid_client_status', 'clients', type_='check')
    op.drop_constraint('valid_billing_status', 'clients', type_='check')
    op.drop_constraint('valid_client_tier', 'clients', type_='check')

    # Drop table
    op.drop_table('clients')
