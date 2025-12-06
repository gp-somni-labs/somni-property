"""Add visual assets to quotes (floor plans, 3D scans, implementation photos)

Revision ID: 024_add_quote_visual_assets
Revises: 939ef182bbe1
Create Date: 2025-11-21 04:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '024_add_quote_visual_assets'
down_revision = '939ef182bbe1'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add visual asset fields to quotes table for immersive quote experience

    Supports:
    - Floor plans (2D architectural drawings)
    - 3D scans (Polycam embeds)
    - Implementation photos (contractor's planned approach)
    - Comparison photos (before/after examples)
    """

    # Add visual asset fields
    op.add_column('quotes', sa.Column('floor_plans', JSONB, nullable=True))
    op.add_column('quotes', sa.Column('polycam_scans', JSONB, nullable=True))
    op.add_column('quotes', sa.Column('implementation_photos', JSONB, nullable=True))
    op.add_column('quotes', sa.Column('comparison_photos', JSONB, nullable=True))

    # Add indexes for querying quotes with visual assets
    op.create_index(
        'idx_quotes_has_floor_plans',
        'quotes',
        [sa.text('(floor_plans IS NOT NULL AND floor_plans != \'[]\'::jsonb)')],
        postgresql_where=sa.text('floor_plans IS NOT NULL')
    )

    op.create_index(
        'idx_quotes_has_3d_scans',
        'quotes',
        [sa.text('(polycam_scans IS NOT NULL AND polycam_scans != \'[]\'::jsonb)')],
        postgresql_where=sa.text('polycam_scans IS NOT NULL')
    )

    print("✅ Added visual asset fields to quotes table")
    print("   - floor_plans: Array of floor plan images/PDFs")
    print("   - polycam_scans: Array of Polycam 3D scan embeds")
    print("   - implementation_photos: Array of contractor's planned approach photos")
    print("   - comparison_photos: Array of before/after reference photos")


def downgrade():
    """Remove visual asset fields"""
    op.drop_index('idx_quotes_has_3d_scans', table_name='quotes')
    op.drop_index('idx_quotes_has_floor_plans', table_name='quotes')

    op.drop_column('quotes', 'comparison_photos')
    op.drop_column('quotes', 'implementation_photos')
    op.drop_column('quotes', 'polycam_scans')
    op.drop_column('quotes', 'floor_plans')

    print("🗑️  Removed visual asset fields from quotes")
