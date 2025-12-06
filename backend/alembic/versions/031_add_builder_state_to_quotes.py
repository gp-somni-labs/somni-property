"""add builder_state column to quotes for device placements persistence

Revision ID: 031
Revises: 030
Create Date: 2025-11-23 16:00:00

This migration adds the builder_state JSON column to the quotes table to persist:
- device_placements: Array of placed devices with spatial coordinates, metadata
- selected_products: Array of selected vendor catalog products
- current_step: Current step in the quote builder workflow
- billing_period: Selected billing period (monthly/annual)

This enables quote editing workflow where users can load a saved quote and
continue where they left off, including all device placements on floorplans/3D models.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add builder_state column to quotes table"""
    op.add_column('quotes', sa.Column('builder_state', JSON, nullable=True))


def downgrade() -> None:
    """Remove builder_state column from quotes table"""
    op.drop_column('quotes', 'builder_state')
