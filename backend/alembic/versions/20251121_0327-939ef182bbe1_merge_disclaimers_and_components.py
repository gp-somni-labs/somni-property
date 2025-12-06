"""merge_disclaimers_and_components

Revision ID: 939ef182bbe1
Revises: 021_add_quote_disclaimers, 023_merge_heads
Create Date: 2025-11-21 03:27:41.875266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '939ef182bbe1'
down_revision = ('021_add_quote_disclaimers', '023_merge_heads')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
