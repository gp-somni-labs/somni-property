"""Normalize hub types to PROPERTY_HUB and RESIDENTIAL

Revision ID: 011_normalize_hub_types
Revises: 010_add_approval_workflow
Create Date: 2025-11-18

This migration simplifies the hub taxonomy from the confusing tier_0/tier_2/tier_3
nomenclature to a clearer two-type system:
- PROPERTY_HUB: Multi-unit buildings (formerly tier_2_property)
- RESIDENTIAL: Single-family homes/apartments (formerly tier_0_standalone and tier_3_residential)

Rationale:
- Only two distinct use cases exist
- "Tier" terminology was confusing and implementation-focused rather than user-focused
- Edge case: tier_0 (standalone self-managed) and tier_3 (deployed residential) are
  functionally the same from the user's perspective

Migration strategy:
1. Update all existing records to new values
2. Update the constraint to use new enum values
3. Model will be updated separately to reflect new enum
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_normalize_hub_types'
down_revision = '010_add_approval_workflow'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Drop old constraint FIRST (must do this before updating data)
    op.execute('ALTER TABLE property_edge_nodes DROP CONSTRAINT IF EXISTS valid_hub_type')

    # Step 2: Migrate existing data
    # tier_0_standalone → RESIDENTIAL (standalone home)
    op.execute("""
        UPDATE property_edge_nodes
        SET hub_type = 'RESIDENTIAL'
        WHERE hub_type = 'tier_0_standalone'
    """)

    # tier_2_property → PROPERTY_HUB (multi-unit building)
    op.execute("""
        UPDATE property_edge_nodes
        SET hub_type = 'PROPERTY_HUB'
        WHERE hub_type = 'tier_2_property'
    """)

    # tier_3_residential → RESIDENTIAL (deployed residential)
    op.execute("""
        UPDATE property_edge_nodes
        SET hub_type = 'RESIDENTIAL'
        WHERE hub_type = 'tier_3_residential'
    """)

    # Step 3: Add new constraint with simplified enum
    op.execute("""
        ALTER TABLE property_edge_nodes ADD CONSTRAINT valid_hub_type
        CHECK (hub_type IN ('PROPERTY_HUB', 'RESIDENTIAL'))
    """)

    print("✅ Normalized hub types:")
    print("   - tier_0_standalone, tier_3_residential → RESIDENTIAL")
    print("   - tier_2_property → PROPERTY_HUB")


def downgrade():
    # WARNING: Downgrade loses information about which RESIDENTIAL hubs
    # were originally tier_0 vs tier_3. We arbitrarily map all to tier_3.

    # Step 1: Migrate data back (with data loss warning)
    op.execute("""
        UPDATE property_edge_nodes
        SET hub_type = 'tier_3_residential'
        WHERE hub_type = 'RESIDENTIAL'
    """)

    op.execute("""
        UPDATE property_edge_nodes
        SET hub_type = 'tier_2_property'
        WHERE hub_type = 'PROPERTY_HUB'
    """)

    # Step 2: Drop new constraint
    op.execute('ALTER TABLE property_edge_nodes DROP CONSTRAINT IF EXISTS valid_hub_type')

    # Step 3: Restore old constraint
    op.execute("""
        ALTER TABLE property_edge_nodes ADD CONSTRAINT valid_hub_type
        CHECK (hub_type IN ('tier_0_standalone', 'tier_2_property', 'tier_3_residential'))
    """)

    print("⚠️ Downgraded hub types (data loss: all RESIDENTIAL → tier_3_residential)")
