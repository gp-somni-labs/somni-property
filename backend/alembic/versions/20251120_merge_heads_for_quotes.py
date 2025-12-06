"""Merge multiple heads before quote system

Revision ID: 20251120_merge_heads_for_quotes
Revises: 013_add_work_order_tasks_materials, 015_fix_documents_schema, 016_add_client_type
Create Date: 2025-11-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251120_merge_heads_for_quotes'
down_revision = ('013_add_work_order_tasks_materials', '015_fix_documents_schema', '016_add_client_type')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration - no schema changes needed
    pass


def downgrade() -> None:
    # Merge migration - no schema changes needed
    pass
