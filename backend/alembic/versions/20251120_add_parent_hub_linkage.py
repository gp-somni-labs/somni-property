"""Add parent hub linkage for multi-unit buildings

Revision ID: 20251120_add_parent_hub_linkage
Revises: 012_payment_linkage_invariants
Create Date: 2025-11-20

This migration adds parent_hub_id to PropertyEdgeNode to support the parent/child
hub relationship for multi-unit buildings.

Use Case:
- Property Hub (PROPERTY_HUB): Manages a multi-unit building (e.g., apartment complex)
- Residential Hubs (RESIDENTIAL): Individual apartment units within the building
- Each residential hub links to its parent property hub via parent_hub_id

Example Hierarchy:
  Building: 123 Main St (Property Hub)
    ├── Apt 1A (Residential Hub, parent_hub_id → Building Hub)
    ├── Apt 2B (Residential Hub, parent_hub_id → Building Hub)
    └── Apt 3C (Residential Hub, parent_hub_id → Building Hub)

Rationale:
- Enables aggregated reporting across all units in a building
- Supports shared building-level services (access control, parking, amenities)
- Allows residential hubs to inherit configuration from parent property hub
- Maintains flexibility for standalone residential hubs (parent_hub_id = NULL)

Database Changes:
1. Add parent_hub_id column (nullable GUID, FK to property_edge_nodes.id)
2. Create foreign key constraint with ON DELETE SET NULL (preserve orphaned hubs)
3. Create index on parent_hub_id for efficient parent/child queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '20251120_add_parent_hub_linkage'
down_revision = '012_payment_linkage_invariants'
branch_labels = None
depends_on = None


def upgrade():
    """Add parent_hub_id column for multi-unit building hub hierarchies"""

    # Step 1: Add parent_hub_id column (nullable, allows existing records)
    op.add_column(
        'property_edge_nodes',
        sa.Column('parent_hub_id', UUID(as_uuid=True), nullable=True)
    )

    # Step 2: Create foreign key constraint
    # ON DELETE SET NULL: If parent hub is deleted, child hubs remain but lose parent link
    op.create_foreign_key(
        'fk_property_edge_nodes_parent_hub_id',
        'property_edge_nodes',
        'property_edge_nodes',
        ['parent_hub_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Step 3: Create index for efficient parent/child queries
    op.create_index(
        'idx_property_edge_nodes_parent_hub_id',
        'property_edge_nodes',
        ['parent_hub_id']
    )

    print("✅ Added parent_hub_id column to property_edge_nodes")
    print("   - Nullable: allows standalone residential hubs")
    print("   - Foreign key: self-referential to property_edge_nodes.id")
    print("   - Index: optimized for parent/child hierarchy queries")
    print("   - Use case: residential hubs link to property hub in multi-unit buildings")


def downgrade():
    """Remove parent_hub_id column and related constraints"""

    # Step 1: Drop index
    op.drop_index('idx_property_edge_nodes_parent_hub_id', table_name='property_edge_nodes')

    # Step 2: Drop foreign key constraint
    op.drop_constraint('fk_property_edge_nodes_parent_hub_id', 'property_edge_nodes', type_='foreignkey')

    # Step 3: Drop column
    op.drop_column('property_edge_nodes', 'parent_hub_id')

    print("⚠️ Removed parent_hub_id column from property_edge_nodes")
    print("   - Data loss: all parent/child hub relationships removed")
