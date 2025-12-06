"""merge_013_and_014

Revision ID: caa2a763b596
Revises: 013_fix_contractors_schema, 014_add_hub_spoke_federation
Create Date: 2025-11-20 14:11:07.685038

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'caa2a763b596'
down_revision = ('013_fix_contractors_schema', '014_add_hub_spoke_federation')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
