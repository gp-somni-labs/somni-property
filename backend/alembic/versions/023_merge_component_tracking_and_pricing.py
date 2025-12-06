"""Merge component tracking and pricing tiers migrations

Revision ID: 023_merge_heads
Revises: 022_add_installed_somni_components, 015_seed_pricing_tiers
Create Date: 2025-11-21 03:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023_merge_heads'
down_revision = ('022_add_installed_somni_components', '015_seed_pricing_tiers')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no schema changes needed
    pass


def downgrade():
    # This is a merge migration - no schema changes needed
    pass
