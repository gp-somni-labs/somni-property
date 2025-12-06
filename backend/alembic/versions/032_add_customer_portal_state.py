"""add customer_portal_state column to quotes for customer portal progress tracking

Revision ID: 032
Revises: 031
Create Date: 2025-11-23 17:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = '032'
down_revision = '031'

def upgrade() -> None:
    """Add customer_portal_state column to quotes table for tracking customer progress"""
    op.add_column('quotes', sa.Column('customer_portal_state', JSON, nullable=True))

def downgrade() -> None:
    """Remove customer_portal_state column from quotes table"""
    op.drop_column('quotes', 'customer_portal_state')
