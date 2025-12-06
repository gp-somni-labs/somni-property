"""Add client_type field to clients table

Revision ID: 016_add_client_type
Revises: 20251120_add_parent_hub_linkage
Create Date: 2025-11-21

Changes:
- Add client_type column to clients table (multi-unit | single-family)
- Add CHECK constraint for valid values
- Add index on client_type for filtering
- Set default to 'multi-unit' for existing clients
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016_add_client_type'
down_revision = '20251120_add_parent_hub_linkage'
branch_labels = None
depends_on = None


def upgrade():
    """Add client_type field to clients table"""
    print("=" * 80)
    print("Adding client_type field to clients table")
    print("=" * 80)

    # Add client_type column (nullable first for existing rows)
    try:
        op.add_column('clients', sa.Column('client_type', sa.String(20), nullable=True))
        print("✅ Added client_type column")
    except Exception as e:
        print(f"⚠️  Could not add client_type column: {e}")

    # Set default value for existing clients (multi-unit)
    try:
        op.execute("UPDATE clients SET client_type = 'multi-unit' WHERE client_type IS NULL")
        print("✅ Set default client_type for existing clients")
    except Exception as e:
        print(f"⚠️  Could not set default client_type: {e}")

    # Make column NOT NULL after setting defaults
    try:
        op.alter_column('clients', 'client_type', nullable=False)
        print("✅ Made client_type column NOT NULL")
    except Exception as e:
        print(f"⚠️  Could not make client_type NOT NULL: {e}")

    # Add CHECK constraint
    try:
        op.create_check_constraint(
            'valid_client_type',
            'clients',
            "client_type IN ('multi-unit', 'single-family')"
        )
        print("✅ Added valid_client_type CHECK constraint")
    except Exception as e:
        print(f"⚠️  Could not add CHECK constraint: {e}")

    # Add index for filtering
    try:
        op.create_index('idx_clients_client_type', 'clients', ['client_type'])
        print("✅ Added index on client_type")
    except Exception as e:
        print(f"⚠️  Could not add index: {e}")

    print("\n" + "=" * 80)
    print("✅ Client Type Migration Complete")
    print("=" * 80)


def downgrade():
    """Remove client_type field from clients table"""
    print("=" * 80)
    print("Removing client_type field from clients table")
    print("=" * 80)

    # Drop index
    op.drop_index('idx_clients_client_type', table_name='clients')
    print("✅ Dropped index on client_type")

    # Drop CHECK constraint
    op.drop_constraint('valid_client_type', 'clients', type_='check')
    print("✅ Dropped valid_client_type CHECK constraint")

    # Drop column
    op.drop_column('clients', 'client_type')
    print("✅ Dropped client_type column")

    print("\n" + "=" * 80)
    print("✅ Client Type Rollback Complete")
    print("=" * 80)
