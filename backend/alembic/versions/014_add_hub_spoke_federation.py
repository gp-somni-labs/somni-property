"""Add Hub-Spoke federation metadata to operational models

Revision ID: 014_add_hub_spoke_federation
Revises: 012_payment_linkage_invariants
Create Date: 2025-01-20

This migration implements Hub-Spoke Federation Architecture by adding
federation metadata fields to all operational entities synced from Spokes.

Adds federation fields to: buildings, units, tenants, leases, work_orders

Changes:
1. Add hub_id (FK to property_edge_nodes) - which Spoke owns this data
2. Add client_id (FK to clients) - denormalized for fast queries
3. Add sync tracking fields (synced_at, sync_status, sync_error_message)
4. Add origin tracking (created_by_hub, last_modified_by)
5. Add hub override audit trail (hub_override_at, hub_override_by)
6. Add indexes for hub_id, client_id, sync_status, synced_at
7. Add CHECK constraints for sync_status and last_modified_by

Note: Columns are nullable in this migration to allow gradual rollout.
Future migration will backfill data and add NOT NULL constraints.

See: HUB_SPOKE_FEDERATION_SCHEMA.md for complete architecture details.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as GUID

# revision identifiers, used by Alembic.
revision = '014_add_hub_spoke_federation'
down_revision = '012_payment_linkage_invariants'
branch_labels = None
depends_on = None


def upgrade():
    """Add Hub-Spoke federation metadata to operational tables"""

    # Tables to add federation metadata
    tables = ['buildings', 'units', 'tenants', 'leases', 'work_orders']

    print("=" * 80)
    print("Adding Hub-Spoke Federation Metadata")
    print("=" * 80)

    for table in tables:
        print(f"\n📦 Processing table: {table}")

        # Add foreign key columns
        op.add_column(table, sa.Column('hub_id', GUID, nullable=True))
        op.add_column(table, sa.Column('client_id', GUID, nullable=True))
        print(f"  ✅ Added hub_id and client_id columns")

        # Add sync tracking fields
        op.add_column(table, sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=True))
        op.add_column(table, sa.Column('sync_status', sa.String(20), server_default='synced', nullable=True))
        op.add_column(table, sa.Column('sync_error_message', sa.Text, nullable=True))
        print(f"  ✅ Added sync tracking fields")

        # Add origin & authority tracking
        op.add_column(table, sa.Column('created_by_hub', sa.Boolean, server_default='false', nullable=False))
        op.add_column(table, sa.Column('last_modified_by', sa.String(10), server_default='spoke', nullable=True))
        op.add_column(table, sa.Column('hub_override_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column('hub_override_by', sa.String(255), nullable=True))
        print(f"  ✅ Added origin & authority tracking fields")

        # Add foreign key constraints
        op.create_foreign_key(
            f'fk_{table}_hub_id',
            table, 'property_edge_nodes',
            ['hub_id'], ['id'],
            ondelete='CASCADE'
        )
        op.create_foreign_key(
            f'fk_{table}_client_id',
            table, 'clients',
            ['client_id'], ['id'],
            ondelete='CASCADE'
        )
        print(f"  ✅ Added foreign key constraints")

        # Add CHECK constraints
        op.create_check_constraint(
            f'valid_{table}_sync_status',
            table,
            "sync_status IN ('synced', 'pending', 'conflict', 'error', 'stale')"
        )
        op.create_check_constraint(
            f'valid_{table}_last_modified_by',
            table,
            "last_modified_by IN ('hub', 'spoke')"
        )
        print(f"  ✅ Added CHECK constraints")

        # Add indexes for performance
        op.create_index(f'idx_{table}_hub_id', table, ['hub_id'])
        op.create_index(f'idx_{table}_client_id', table, ['client_id'])
        op.create_index(f'idx_{table}_sync_status', table, ['sync_status'])
        op.create_index(f'idx_{table}_synced_at', table, ['synced_at'])
        print(f"  ✅ Added performance indexes")

        print(f"  ✨ {table} federation metadata complete")

    print("\n" + "=" * 80)
    print("✅ Hub-Spoke Federation Migration Complete")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run backfill migration to populate hub_id/client_id from existing data")
    print("2. Add NOT NULL constraints after backfill")
    print("3. Update API endpoints to support hub_id/client_id filtering")
    print("4. Update frontend views to display Hub/Client context")
    print()


def downgrade():
    """Remove Hub-Spoke federation metadata"""

    tables = ['buildings', 'units', 'tenants', 'leases', 'work_orders']

    print("=" * 80)
    print("Rolling back Hub-Spoke Federation Metadata")
    print("=" * 80)

    for table in tables:
        print(f"\n🔄 Rolling back table: {table}")

        # Drop indexes
        op.drop_index(f'idx_{table}_synced_at', table_name=table)
        op.drop_index(f'idx_{table}_sync_status', table_name=table)
        op.drop_index(f'idx_{table}_client_id', table_name=table)
        op.drop_index(f'idx_{table}_hub_id', table_name=table)
        print(f"  ✅ Dropped indexes")

        # Drop CHECK constraints
        op.drop_constraint(f'valid_{table}_last_modified_by', table, type_='check')
        op.drop_constraint(f'valid_{table}_sync_status', table, type_='check')
        print(f"  ✅ Dropped CHECK constraints")

        # Drop foreign key constraints
        op.drop_constraint(f'fk_{table}_client_id', table, type_='foreignkey')
        op.drop_constraint(f'fk_{table}_hub_id', table, type_='foreignkey')
        print(f"  ✅ Dropped foreign key constraints")

        # Drop columns
        op.drop_column(table, 'hub_override_by')
        op.drop_column(table, 'hub_override_at')
        op.drop_column(table, 'last_modified_by')
        op.drop_column(table, 'created_by_hub')
        op.drop_column(table, 'sync_error_message')
        op.drop_column(table, 'sync_status')
        op.drop_column(table, 'synced_at')
        op.drop_column(table, 'client_id')
        op.drop_column(table, 'hub_id')
        print(f"  ✅ Dropped all federation columns")

        print(f"  ✨ {table} rollback complete")

    print("\n" + "=" * 80)
    print("✅ Hub-Spoke Federation Rollback Complete")
    print("=" * 80)
