"""add labor cost fields to quotes

Revision ID: 028_add_labor_cost_fields
Revises: 027_make_total_units_optional
Create Date: 2025-01-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_add_labor_cost_fields'
down_revision = '027_make_total_units_optional'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add labor and installation cost tracking fields to quotes table"""

    # Add labor cost fields
    op.add_column('quotes', sa.Column('total_labor_cost', sa.Numeric(10, 2), server_default='0', nullable=True))
    op.add_column('quotes', sa.Column('total_materials_cost', sa.Numeric(10, 2), server_default='0', nullable=True))
    op.add_column('quotes', sa.Column('total_labor_hours', sa.Numeric(10, 2), server_default='0', nullable=True))

    # Add project timeline fields
    op.add_column('quotes', sa.Column('project_duration_days', sa.Integer(), nullable=True))
    op.add_column('quotes', sa.Column('installation_start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('installation_completion_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove labor cost fields from quotes table"""

    # Remove project timeline fields
    op.drop_column('quotes', 'installation_completion_date')
    op.drop_column('quotes', 'installation_start_date')
    op.drop_column('quotes', 'project_duration_days')

    # Remove labor cost fields
    op.drop_column('quotes', 'total_labor_hours')
    op.drop_column('quotes', 'total_materials_cost')
    op.drop_column('quotes', 'total_labor_cost')
