"""Add Tier 0 (Standalone) hub type

Revision ID: 003_tier_0_standalone
Revises: 002_3tier_architecture
Create Date: 2025-10-31

Adds Tier 0 (Standalone) support for integrating existing self-managed
Home Assistant instances that are not deployed via Kubernetes.

Changes:
1. PropertyEdgeNode.hub_type - Add 'tier_0_standalone' option
   - Tier 0: Self-managed HA instances (existing locations)
   - Tier 2: Property Hubs (K8s stacks for buildings)
   - Tier 3: Residential Hubs (K8s stacks for homes)

Tier 0 nodes are characterized by:
- managed_by_tier1 = False (self-managed)
- auto_update_enabled = False (no automated updates)
- No deployment capabilities (sync-only)
- Connected via Tailscale mesh

This enables registering the user's 5 existing standalone Home Assistant
instances as Tier 0 nodes while maintaining the full fleet management
capabilities for future Tier 2/3 deployments.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '003_tier_0_standalone'
down_revision = '002_3tier_architecture'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing hub_type constraint
    op.execute('ALTER TABLE property_edge_nodes DROP CONSTRAINT IF EXISTS valid_hub_type')

    # Add new constraint including tier_0_standalone
    op.execute("""
        ALTER TABLE property_edge_nodes ADD CONSTRAINT valid_hub_type
        CHECK (hub_type IN ('tier_0_standalone', 'tier_2_property', 'tier_3_residential'))
    """)

    print("✅ Added tier_0_standalone to hub_type constraint")


def downgrade():
    # Drop constraint with tier_0_standalone
    op.execute('ALTER TABLE property_edge_nodes DROP CONSTRAINT IF EXISTS valid_hub_type')

    # Restore original constraint without tier_0_standalone
    op.execute("""
        ALTER TABLE property_edge_nodes ADD CONSTRAINT valid_hub_type
        CHECK (hub_type IN ('tier_2_property', 'tier_3_residential'))
    """)

    print("⚠️ Removed tier_0_standalone from hub_type constraint")
