"""Add 3-Tier Architecture Support

Revision ID: 002_3tier_architecture
Revises: 001_smart_home_services
Create Date: 2025-10-29

Adds 3-tier fleet management architecture support:

1. PropertyEdgeNode updates:
   - hub_type: Tier 2 (Property Hub) vs Tier 3 (Residential Hub)
   - sync_status: Device sync tracking
   - deployed_stack: Which K8s stack is deployed
   - manifest_version: Git commit SHA
   - Fleet management flags and API auth

2. SmartDevice updates:
   - sync_source: Devices primarily synced from Home Assistant
   - synced_from_hub_id: Which Tier 2/3 hub
   - Home Assistant entity data (domain, state, attributes)

3. ServicePackage updates:
   - target_tier: Which hub types can use this package
   - service_versions: K8s service versions
   - manifest_repo_url: GitOps integration

4. New Tables:
   - fleet_deployments: Track K8s stack deployments to hubs
   - device_syncs: Track HA device sync operations

This transforms SomniProperty from a single-instance app into a
3-tier fleet management system orchestrating Tier 2 (Property Hubs)
and Tier 3 (Residential Hubs) Kubernetes clusters.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_3tier_architecture'
down_revision = '001_smart_home_services'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # 1. Update PropertyEdgeNode table with 3-tier architecture fields
    # ========================================================================
    op.add_column('property_edge_nodes', sa.Column('hub_type', sa.String(length=30), nullable=False, server_default='tier_3_residential'))
    op.add_column('property_edge_nodes', sa.Column('sync_status', sa.String(length=20), nullable=False, server_default='never_synced'))
    op.add_column('property_edge_nodes', sa.Column('sync_error_message', sa.Text(), nullable=True))
    op.add_column('property_edge_nodes', sa.Column('deployed_stack', sa.String(length=50), nullable=True))
    op.add_column('property_edge_nodes', sa.Column('manifest_version', sa.String(length=255), nullable=True))
    op.add_column('property_edge_nodes', sa.Column('managed_by_tier1', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('property_edge_nodes', sa.Column('auto_update_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('property_edge_nodes', sa.Column('api_token_hash', sa.String(length=500), nullable=True))
    op.add_column('property_edge_nodes', sa.Column('tailscale_ip', postgresql.INET(), nullable=True))

    # Add check constraints for PropertyEdgeNode
    op.create_check_constraint('valid_hub_type', 'property_edge_nodes', "hub_type IN ('tier_2_property', 'tier_3_residential')")
    op.create_check_constraint('valid_sync_status', 'property_edge_nodes', "sync_status IN ('synced', 'syncing', 'error', 'never_synced')")

    # Add indexes for PropertyEdgeNode
    op.create_index('idx_property_edge_nodes_hub_type', 'property_edge_nodes', ['hub_type'])
    op.create_index('idx_property_edge_nodes_sync_status', 'property_edge_nodes', ['sync_status'])

    # ========================================================================
    # 2. Update SmartDevice table with Home Assistant sync fields
    # ========================================================================
    op.add_column('smart_devices', sa.Column('sync_source', sa.String(length=20), nullable=False, server_default='home_assistant'))
    op.add_column('smart_devices', sa.Column('synced_from_hub_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('smart_devices', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smart_devices', sa.Column('home_assistant_entity_id', sa.String(length=255), nullable=True))
    op.add_column('smart_devices', sa.Column('ha_domain', sa.String(length=50), nullable=True))
    op.add_column('smart_devices', sa.Column('ha_state', sa.String(length=100), nullable=True))
    op.add_column('smart_devices', sa.Column('ha_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('smart_devices', sa.Column('device_name', sa.String(length=255), nullable=True))
    op.add_column('smart_devices', sa.Column('battery_level', sa.Integer(), nullable=True))
    op.add_column('smart_devices', sa.Column('signal_strength', sa.Integer(), nullable=True))
    op.add_column('smart_devices', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('smart_devices', sa.Column('ip_address', postgresql.INET(), nullable=True))
    op.add_column('smart_devices', sa.Column('mac_address', sa.String(length=50), nullable=True))

    # Add foreign key for synced_from_hub_id
    op.create_foreign_key('fk_smart_devices_synced_from_hub', 'smart_devices', 'property_edge_nodes', ['synced_from_hub_id'], ['id'], ondelete='SET NULL')

    # Add check constraint for SmartDevice
    op.create_check_constraint('valid_sync_source', 'smart_devices', "sync_source IN ('home_assistant', 'manual')")

    # Add indexes for SmartDevice
    op.create_index('idx_smart_devices_home_assistant_entity_id', 'smart_devices', ['home_assistant_entity_id'])
    op.create_index('idx_smart_devices_synced_from_hub_id', 'smart_devices', ['synced_from_hub_id'])
    op.create_index('idx_smart_devices_sync_source', 'smart_devices', ['sync_source'])
    op.create_index('idx_smart_devices_last_synced_at', 'smart_devices', ['last_synced_at'])

    # ========================================================================
    # 3. Update ServicePackage table with tier targeting and stack definition
    # ========================================================================
    op.add_column('service_packages', sa.Column('target_tier', sa.String(length=20), nullable=False, server_default='tier_3'))
    op.add_column('service_packages', sa.Column('service_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('service_packages', sa.Column('manifest_repo_url', sa.String(length=500), nullable=True))
    op.add_column('service_packages', sa.Column('manifest_path', sa.String(length=500), nullable=True))

    # Add check constraint for ServicePackage
    op.create_check_constraint('valid_target_tier', 'service_packages', "target_tier IN ('tier_2', 'tier_3', 'both')")

    # Add index for ServicePackage
    op.create_index('idx_service_packages_target_tier', 'service_packages', ['target_tier'])

    # ========================================================================
    # 4. Create FleetDeployment table
    # ========================================================================
    op.create_table(
        'fleet_deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('target_hub_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_hub_type', sa.String(length=30), nullable=False),
        sa.Column('service_package_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manifest_version', sa.String(length=255), nullable=False),
        sa.Column('deployment_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deployment_log', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('initiated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['target_hub_id'], ['property_edge_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_package_id'], ['service_packages.id'], ondelete='RESTRICT'),
        sa.CheckConstraint("deployment_status IN ('pending', 'deploying', 'success', 'failed')", name='valid_deployment_status'),
        sa.CheckConstraint("target_hub_type IN ('tier_2_property', 'tier_3_residential')", name='valid_target_hub_type'),
    )

    # Add indexes for FleetDeployment
    op.create_index('idx_fleet_deployments_target_hub_id', 'fleet_deployments', ['target_hub_id'])
    op.create_index('idx_fleet_deployments_service_package_id', 'fleet_deployments', ['service_package_id'])
    op.create_index('idx_fleet_deployments_status', 'fleet_deployments', ['deployment_status'])
    op.create_index('idx_fleet_deployments_initiated_at', 'fleet_deployments', ['initiated_at'])

    # ========================================================================
    # 5. Create DeviceSync table
    # ========================================================================
    op.create_table(
        'device_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_hub_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('sync_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('devices_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('devices_added', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('devices_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('devices_removed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_hub_id'], ['property_edge_nodes.id'], ondelete='CASCADE'),
        sa.CheckConstraint("sync_status IN ('success', 'partial', 'failed')", name='valid_sync_status'),
    )

    # Add indexes for DeviceSync
    op.create_index('idx_device_syncs_source_hub_id', 'device_syncs', ['source_hub_id'])
    op.create_index('idx_device_syncs_sync_started_at', 'device_syncs', ['sync_started_at'])
    op.create_index('idx_device_syncs_sync_status', 'device_syncs', ['sync_status'])


def downgrade() -> None:
    # Drop DeviceSync table
    op.drop_index('idx_device_syncs_sync_status', table_name='device_syncs')
    op.drop_index('idx_device_syncs_sync_started_at', table_name='device_syncs')
    op.drop_index('idx_device_syncs_source_hub_id', table_name='device_syncs')
    op.drop_table('device_syncs')

    # Drop FleetDeployment table
    op.drop_index('idx_fleet_deployments_initiated_at', table_name='fleet_deployments')
    op.drop_index('idx_fleet_deployments_status', table_name='fleet_deployments')
    op.drop_index('idx_fleet_deployments_service_package_id', table_name='fleet_deployments')
    op.drop_index('idx_fleet_deployments_target_hub_id', table_name='fleet_deployments')
    op.drop_table('fleet_deployments')

    # Remove ServicePackage fields
    op.drop_index('idx_service_packages_target_tier', table_name='service_packages')
    op.drop_constraint('valid_target_tier', 'service_packages', type_='check')
    op.drop_column('service_packages', 'manifest_path')
    op.drop_column('service_packages', 'manifest_repo_url')
    op.drop_column('service_packages', 'service_versions')
    op.drop_column('service_packages', 'target_tier')

    # Remove SmartDevice fields
    op.drop_index('idx_smart_devices_last_synced_at', table_name='smart_devices')
    op.drop_index('idx_smart_devices_sync_source', table_name='smart_devices')
    op.drop_index('idx_smart_devices_synced_from_hub_id', table_name='smart_devices')
    op.drop_index('idx_smart_devices_home_assistant_entity_id', table_name='smart_devices')
    op.drop_constraint('valid_sync_source', 'smart_devices', type_='check')
    op.drop_constraint('fk_smart_devices_synced_from_hub', 'smart_devices', type_='foreignkey')
    op.drop_column('smart_devices', 'mac_address')
    op.drop_column('smart_devices', 'ip_address')
    op.drop_column('smart_devices', 'location')
    op.drop_column('smart_devices', 'signal_strength')
    op.drop_column('smart_devices', 'battery_level')
    op.drop_column('smart_devices', 'device_name')
    op.drop_column('smart_devices', 'ha_attributes')
    op.drop_column('smart_devices', 'ha_state')
    op.drop_column('smart_devices', 'ha_domain')
    op.drop_column('smart_devices', 'home_assistant_entity_id')
    op.drop_column('smart_devices', 'last_synced_at')
    op.drop_column('smart_devices', 'synced_from_hub_id')
    op.drop_column('smart_devices', 'sync_source')

    # Remove PropertyEdgeNode fields
    op.drop_index('idx_property_edge_nodes_sync_status', table_name='property_edge_nodes')
    op.drop_index('idx_property_edge_nodes_hub_type', table_name='property_edge_nodes')
    op.drop_constraint('valid_sync_status', 'property_edge_nodes', type_='check')
    op.drop_constraint('valid_hub_type', 'property_edge_nodes', type_='check')
    op.drop_column('property_edge_nodes', 'tailscale_ip')
    op.drop_column('property_edge_nodes', 'api_token_hash')
    op.drop_column('property_edge_nodes', 'auto_update_enabled')
    op.drop_column('property_edge_nodes', 'managed_by_tier1')
    op.drop_column('property_edge_nodes', 'manifest_version')
    op.drop_column('property_edge_nodes', 'deployed_stack')
    op.drop_column('property_edge_nodes', 'sync_error_message')
    op.drop_column('property_edge_nodes', 'sync_status')
    op.drop_column('property_edge_nodes', 'hub_type')
