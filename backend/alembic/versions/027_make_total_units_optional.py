"""Make total_units optional for hardware quotes

Revision ID: 027_make_total_units_optional
Revises: 026_add_edge_node_commands
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '027_make_total_units_optional'
down_revision = '026_add_edge_node_commands'
branch_labels = None
depends_on = None


def upgrade():
    # Make total_units nullable and set default to 1
    op.alter_column('quotes', 'total_units',
                    existing_type=sa.Integer(),
                    nullable=True,
                    server_default='1')


def downgrade():
    # Revert: make total_units non-nullable
    # First, update any NULL values to 1
    op.execute("UPDATE quotes SET total_units = 1 WHERE total_units IS NULL")

    # Then make column non-nullable
    op.alter_column('quotes', 'total_units',
                    existing_type=sa.Integer(),
                    nullable=False,
                    server_default=None)
