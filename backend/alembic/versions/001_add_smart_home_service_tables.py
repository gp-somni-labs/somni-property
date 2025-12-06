"""Add Smart Home Service tables

Revision ID: 001_smart_home_services
Revises:
Create Date: 2025-10-29

Adds 5 new tables for Smart Home as a Service (SHaaS) functionality:
- service_packages: Tiered service offerings (Basic/Premium/Enterprise)
- service_contracts: Service agreements linking clients to packages
- installations: Installation project tracking
- smart_devices: Smart device inventory with MQTT/HA integration
- property_edge_nodes: Home Assistant instances managing properties

Also extends the tenants table with service subscription fields.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_smart_home_services'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # 1. Extend tenants table with Smart Home Service fields
    # ========================================================================
    op.add_column('tenants', sa.Column('client_type', sa.String(length=30), nullable=False, server_default='rental_tenant'))
    op.add_column('tenants', sa.Column('service_tier', sa.String(length=50), nullable=True))
    op.add_column('tenants', sa.Column('subscription_status', sa.String(length=20), nullable=False, server_default='inactive'))
    op.add_column('tenants', sa.Column('service_contract_start', sa.Date(), nullable=True))
    op.add_column('tenants', sa.Column('service_contract_end', sa.Date(), nullable=True))
    op.add_column('tenants', sa.Column('billing_cycle', sa.String(length=20), nullable=False, server_default='monthly'))

    # Add constraints for tenant service fields
    op.create_check_constraint(
        'valid_client_type',
        'tenants',
        "client_type IN ('rental_tenant', 'service_subscriber', 'both')"
    )
    op.create_check_constraint(
        'valid_subscription_status',
        'tenants',
        "subscription_status IN ('inactive', 'active', 'paused', 'cancelled')"
    )
    op.create_check_constraint(
        'valid_billing_cycle',
        'tenants',
        "billing_cycle IN ('monthly', 'annual', 'one-time')"
    )

    # Add indexes for tenant service fields
    op.create_index('idx_tenants_client_type', 'tenants', ['client_type'])
    op.create_index('idx_tenants_subscription_status', 'tenants', ['subscription_status'])

    # ========================================================================
    # 2. Create service_packages table
    # ========================================================================
    op.create_table(
        'service_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('monthly_fee', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('installation_fee', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('annual_discount_percent', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('included_services', postgresql.JSONB(), nullable=True),
        sa.Column('included_device_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sla_response_time_hours', sa.Integer(), nullable=False, server_default='48'),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_service_packages_active', 'service_packages', ['active'])
    op.create_index('idx_service_packages_monthly_fee', 'service_packages', ['monthly_fee'])

    # ========================================================================
    # 3. Create service_contracts table
    # ========================================================================
    op.create_table(
        'service_contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('package_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_packages.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contract_type', sa.String(length=20), nullable=False, server_default='monthly'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('monthly_fee', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('installation_fee', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('installation_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('installation_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_check_constraint(
        'valid_contract_type',
        'service_contracts',
        "contract_type IN ('monthly', 'annual', 'project')"
    )
    op.create_check_constraint(
        'valid_contract_status',
        'service_contracts',
        "status IN ('draft', 'active', 'paused', 'cancelled', 'completed')"
    )
    op.create_index('idx_service_contracts_client', 'service_contracts', ['client_id'])
    op.create_index('idx_service_contracts_property', 'service_contracts', ['property_id'])
    op.create_index('idx_service_contracts_status', 'service_contracts', ['status'])
    op.create_index('idx_service_contracts_start_date', 'service_contracts', ['start_date'])

    # ========================================================================
    # 4. Create installations table
    # ========================================================================
    op.create_table(
        'installations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_contracts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='scheduled'),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('installer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('installer_name', sa.String(length=255), nullable=True),
        sa.Column('devices_to_install', postgresql.JSONB(), nullable=True),
        sa.Column('devices_installed', postgresql.JSONB(), nullable=True),
        sa.Column('installation_notes', sa.Text(), nullable=True),
        sa.Column('completion_certificate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('labor_hours', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('labor_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('materials_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_check_constraint(
        'valid_installation_status',
        'installations',
        "status IN ('scheduled', 'in_progress', 'completed', 'cancelled')"
    )
    op.create_index('idx_installations_contract', 'installations', ['contract_id'])
    op.create_index('idx_installations_status', 'installations', ['status'])
    op.create_index('idx_installations_scheduled_date', 'installations', ['scheduled_date'])

    # ========================================================================
    # 5. Create property_edge_nodes table
    # ========================================================================
    op.create_table(
        'property_edge_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('node_type', sa.String(length=30), nullable=False, server_default='home_assistant'),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('tailscale_hostname', sa.String(length=255), nullable=True),
        sa.Column('api_token', sa.String(length=500), nullable=True),
        sa.Column('api_url', sa.String(length=500), nullable=True),
        sa.Column('mqtt_broker_host', sa.String(length=255), nullable=True),
        sa.Column('mqtt_broker_port', sa.Integer(), nullable=False, server_default='1883'),
        sa.Column('mqtt_topics', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='offline'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('device_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('automation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uptime_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resource_usage', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_check_constraint(
        'valid_node_type',
        'property_edge_nodes',
        "node_type IN ('home_assistant', 'mqtt', 'custom')"
    )
    op.create_check_constraint(
        'valid_node_status',
        'property_edge_nodes',
        "status IN ('online', 'offline', 'error', 'maintenance')"
    )
    op.create_index('idx_edge_nodes_property', 'property_edge_nodes', ['property_id'])
    op.create_index('idx_edge_nodes_status', 'property_edge_nodes', ['status'])
    op.create_index('idx_edge_nodes_last_heartbeat', 'property_edge_nodes', ['last_heartbeat'])

    # ========================================================================
    # 6. Create smart_devices table
    # ========================================================================
    op.create_table(
        'smart_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('service_contract_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_contracts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('edge_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_edge_nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=False),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('installation_date', sa.Date(), nullable=True),
        sa.Column('warranty_expiration', sa.Date(), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('mqtt_topic', sa.String(length=255), nullable=True),
        sa.Column('ha_entity_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('health_status', sa.String(length=20), nullable=False, server_default='healthy'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replacement_due', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_check_constraint(
        'valid_device_status',
        'smart_devices',
        "status IN ('active', 'inactive', 'maintenance', 'failed', 'retired')"
    )
    op.create_check_constraint(
        'valid_device_health',
        'smart_devices',
        "health_status IN ('healthy', 'warning', 'critical', 'unknown')"
    )
    op.create_index('idx_smart_devices_property', 'smart_devices', ['property_id'])
    op.create_index('idx_smart_devices_client', 'smart_devices', ['client_id'])
    op.create_index('idx_smart_devices_edge_node', 'smart_devices', ['edge_node_id'])
    op.create_index('idx_smart_devices_type', 'smart_devices', ['device_type'])
    op.create_index('idx_smart_devices_status', 'smart_devices', ['status'])
    op.create_index('idx_smart_devices_health', 'smart_devices', ['health_status'])
    op.create_index('idx_smart_devices_last_seen', 'smart_devices', ['last_seen'])


def downgrade() -> None:
    # ========================================================================
    # Drop tables in reverse order (respecting foreign keys)
    # ========================================================================
    op.drop_table('smart_devices')
    op.drop_table('installations')
    op.drop_table('service_contracts')
    op.drop_table('property_edge_nodes')
    op.drop_table('service_packages')

    # ========================================================================
    # Remove tenant service fields
    # ========================================================================
    op.drop_index('idx_tenants_subscription_status', 'tenants')
    op.drop_index('idx_tenants_client_type', 'tenants')
    op.drop_constraint('valid_billing_cycle', 'tenants')
    op.drop_constraint('valid_subscription_status', 'tenants')
    op.drop_constraint('valid_client_type', 'tenants')
    op.drop_column('tenants', 'billing_cycle')
    op.drop_column('tenants', 'service_contract_end')
    op.drop_column('tenants', 'service_contract_start')
    op.drop_column('tenants', 'subscription_status')
    op.drop_column('tenants', 'service_tier')
    op.drop_column('tenants', 'client_type')
