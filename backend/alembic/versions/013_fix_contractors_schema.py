"""013_fix_contractors_schema

Revision ID: 013_fix_contractors_schema
Revises: 012_payment_linkage_invariants
Create Date: 2025-11-20 00:00:00.000000

Fix contractors table schema to match current model definition
- Drop legacy columns: name, rating, insurance_expiry
- Make 'company_name' NOT NULL
- Ensure phone is NOT NULL
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_fix_contractors_schema'
down_revision = '012_payment_linkage_invariants'
branch_labels = None
depends_on = None


def upgrade():
    """Fix contractors table schema to match model"""

    # NOTE: This migration is now a no-op because migration 009_add_staff_contractors
    # drops and recreates the contractors table with the correct schema.
    # The contractors table already has the correct schema at this point.

    print("ℹ️  Skipping contractors schema fixes - table was already recreated with correct schema in migration 009")
    print("✅ Contractors table schema migration completed (no-op)")


def downgrade():
    """Revert contractors table schema changes"""

    # Add back legacy columns
    op.add_column('contractors',
        sa.Column('name', sa.String(255), nullable=True)
    )
    op.add_column('contractors',
        sa.Column('rating', sa.Integer(), nullable=True)
    )
    op.add_column('contractors',
        sa.Column('insurance_expiry', sa.Date(), nullable=True)
    )

    # Make columns nullable again
    op.alter_column('contractors', 'phone',
                    existing_type=sa.String(20),
                    nullable=True)
    op.alter_column('contractors', 'company_name',
                    existing_type=sa.String(255),
                    nullable=True)

    print("✅ Reverted contractors table schema changes")
