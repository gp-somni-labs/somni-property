"""Add payment linkage invariants - EPIC D

Revision ID: 012_payment_linkage_invariants
Revises: 011_normalize_hub_types
Create Date: 2025-11-18

This migration implements EPIC D: Add Payment Linkage Invariants

Ensures that payments link properly to tenants & units via leases with consistency validation.

Changes:
1. Add tenant_id column (FK to tenants.id) to rent_payments
2. Add unit_id column (FK to units.id) to rent_payments
3. Backfill existing data from lease relationships
4. Add NOT NULL constraints after backfill
5. Create trigger to enforce invariant: tenant_id and unit_id must match lease's tenant_id and unit_id

Invariant Enforcement:
- Database trigger validates that rent_payment.tenant_id matches leases.tenant_id
- Database trigger validates that rent_payment.unit_id matches leases.unit_id
- Prevents data inconsistency at the database level
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as GUID


# revision identifiers, used by Alembic.
revision = '012_payment_linkage_invariants'
down_revision = '011_normalize_hub_types'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add new columns (nullable initially)
    op.add_column('rent_payments', sa.Column('tenant_id', GUID, nullable=True))
    op.add_column('rent_payments', sa.Column('unit_id', GUID, nullable=True))

    print("✅ Added tenant_id and unit_id columns to rent_payments")

    # Step 2: Backfill data from leases table
    op.execute('''
        UPDATE rent_payments rp
        SET tenant_id = l.tenant_id, unit_id = l.unit_id
        FROM leases l
        WHERE rp.lease_id = l.id
    ''')

    print("✅ Backfilled tenant_id and unit_id from leases")

    # Step 3: Set NOT NULL constraints
    op.alter_column('rent_payments', 'tenant_id', nullable=False)
    op.alter_column('rent_payments', 'unit_id', nullable=False)

    print("✅ Added NOT NULL constraints")

    # Step 4: Add foreign key constraints
    op.create_foreign_key(
        'fk_rent_payments_tenant_id',
        'rent_payments', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_rent_payments_unit_id',
        'rent_payments', 'units',
        ['unit_id'], ['id'],
        ondelete='CASCADE'
    )

    print("✅ Added foreign key constraints")

    # Step 5: Add indexes for foreign keys
    op.create_index('idx_rent_payments_tenant_id', 'rent_payments', ['tenant_id'])
    op.create_index('idx_rent_payments_unit_id', 'rent_payments', ['unit_id'])

    print("✅ Added indexes for tenant_id and unit_id")

    # Step 6: Create trigger function to enforce invariant
    op.execute('''
        CREATE OR REPLACE FUNCTION check_payment_lease_consistency()
        RETURNS TRIGGER AS $$
        DECLARE
            lease_tenant_id UUID;
            lease_unit_id UUID;
        BEGIN
            -- Get tenant_id and unit_id from the lease
            SELECT tenant_id, unit_id INTO lease_tenant_id, lease_unit_id
            FROM leases
            WHERE id = NEW.lease_id;

            -- If lease not found, raise error
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Lease with id % not found', NEW.lease_id;
            END IF;

            -- Check tenant_id matches
            IF NEW.tenant_id != lease_tenant_id THEN
                RAISE EXCEPTION 'tenant_id % does not match lease tenant_id %',
                    NEW.tenant_id, lease_tenant_id;
            END IF;

            -- Check unit_id matches
            IF NEW.unit_id != lease_unit_id THEN
                RAISE EXCEPTION 'unit_id % does not match lease unit_id %',
                    NEW.unit_id, lease_unit_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')

    print("✅ Created trigger function check_payment_lease_consistency()")

    # Step 7: Create trigger
    op.execute('''
        CREATE TRIGGER enforce_payment_lease_consistency
        BEFORE INSERT OR UPDATE ON rent_payments
        FOR EACH ROW
        EXECUTE FUNCTION check_payment_lease_consistency();
    ''')

    print("✅ Created trigger enforce_payment_lease_consistency")
    print("")
    print("🎯 EPIC D Complete: Payment Linkage Invariants Enforced")
    print("   - tenant_id and unit_id columns added")
    print("   - Foreign keys and indexes created")
    print("   - Database trigger ensures consistency with lease data")


def downgrade():
    # Step 1: Drop trigger
    op.execute('DROP TRIGGER IF EXISTS enforce_payment_lease_consistency ON rent_payments')

    # Step 2: Drop trigger function
    op.execute('DROP FUNCTION IF EXISTS check_payment_lease_consistency()')

    # Step 3: Drop indexes
    op.drop_index('idx_rent_payments_unit_id', 'rent_payments')
    op.drop_index('idx_rent_payments_tenant_id', 'rent_payments')

    # Step 4: Drop foreign keys
    op.drop_constraint('fk_rent_payments_unit_id', 'rent_payments', type_='foreignkey')
    op.drop_constraint('fk_rent_payments_tenant_id', 'rent_payments', type_='foreignkey')

    # Step 5: Drop columns
    op.drop_column('rent_payments', 'unit_id')
    op.drop_column('rent_payments', 'tenant_id')

    print("⚠️ Downgraded: Removed payment linkage invariants")
