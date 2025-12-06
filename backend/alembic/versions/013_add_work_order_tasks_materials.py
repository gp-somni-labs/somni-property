"""Add work order tasks and materials - WO-001

Revision ID: 013_wo_tasks_mat
Revises: 012_payment_linkage_invariants
Create Date: 2025-11-20

This migration implements WO-001: Enhance Work Orders with Tasks, Materials, and Timeline

Changes:
1. Create work_order_tasks table for subtasks with estimates and actuals
2. Create work_order_materials table for materials with costs
3. Add indexes for efficient querying

Tables:
- work_order_tasks: Subtasks with estimate_hours, actual_hours, sequence, status
- work_order_materials: Materials with qty, unit_cost, extended_cost
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as GUID

# revision identifiers, used by Alembic.
revision = '013_wo_tasks_mat'
down_revision = '012_payment_linkage_invariants'
branch_labels = None
depends_on = None


def upgrade():
    # Create work_order_tasks table
    op.create_table(
        'work_order_tasks',
        sa.Column('id', GUID, primary_key=True),
        sa.Column('work_order_id', GUID, sa.ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('estimate_hours', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_hours', sa.Numeric(10, 2), nullable=True),
        sa.Column('sequence', sa.Integer, default=0),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name='valid_task_status'
        )
    )

    # Add indexes for work_order_tasks
    op.create_index(
        'idx_work_order_tasks_work_order_id',
        'work_order_tasks',
        ['work_order_id']
    )
    op.create_index(
        'idx_work_order_tasks_sequence',
        'work_order_tasks',
        ['work_order_id', 'sequence']
    )

    print("✅ Created work_order_tasks table with indexes")

    # Create work_order_materials table
    op.create_table(
        'work_order_materials',
        sa.Column('id', GUID, primary_key=True),
        sa.Column('work_order_id', GUID, sa.ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item', sa.String(255), nullable=False),
        sa.Column('qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=False),
        sa.Column('extended_cost', sa.Numeric(10, 2), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Add index for work_order_materials
    op.create_index(
        'idx_work_order_materials_work_order_id',
        'work_order_materials',
        ['work_order_id']
    )

    print("✅ Created work_order_materials table with indexes")


def downgrade():
    # Drop work_order_materials table
    op.drop_index('idx_work_order_materials_work_order_id', table_name='work_order_materials')
    op.drop_table('work_order_materials')

    print("✅ Dropped work_order_materials table")

    # Drop work_order_tasks table
    op.drop_index('idx_work_order_tasks_sequence', table_name='work_order_tasks')
    op.drop_index('idx_work_order_tasks_work_order_id', table_name='work_order_tasks')
    op.drop_table('work_order_tasks')

    print("✅ Dropped work_order_tasks table")
