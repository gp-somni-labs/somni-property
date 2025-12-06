"""Add project phases for incremental deposit planning

Revision ID: 020_add_project_phases
Revises: 20251120_merge_heads_for_quotes
Create Date: 2025-11-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '020_add_project_phases'
down_revision = '20251120_merge_heads_for_quotes'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # PROJECT TIMELINES TABLE
    # ========================================================================
    op.create_table(
        'project_timelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False, unique=True),

        # Timeline details
        sa.Column('project_name', sa.String(255), nullable=False),
        sa.Column('project_description', sa.Text),

        # Overall timeline
        sa.Column('planned_start_date', sa.DateTime(timezone=True)),
        sa.Column('planned_completion_date', sa.DateTime(timezone=True)),
        sa.Column('actual_start_date', sa.DateTime(timezone=True)),
        sa.Column('actual_completion_date', sa.DateTime(timezone=True)),

        # Duration estimates
        sa.Column('total_estimated_days', sa.Integer),
        sa.Column('total_actual_days', sa.Integer),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='planning'),
        sa.Column('completion_percentage', sa.Integer, nullable=False, server_default='0'),

        # Financial summary
        sa.Column('total_project_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_deposits_required', sa.Numeric(12, 2)),
        sa.Column('total_deposits_received', sa.Numeric(12, 2), server_default='0'),
        sa.Column('total_paid', sa.Numeric(12, 2), server_default='0'),
        sa.Column('balance_remaining', sa.Numeric(12, 2)),

        # Phase summary
        sa.Column('total_phases', sa.Integer, server_default='0'),
        sa.Column('phases_unlocked', sa.Integer, server_default='0'),
        sa.Column('phases_completed', sa.Integer, server_default='0'),

        # Team assignment
        sa.Column('project_manager', sa.String(255)),
        sa.Column('lead_technician', sa.String(255)),
        sa.Column('assigned_team', postgresql.JSON),

        # Customer relationship
        sa.Column('customer_contact_name', sa.String(255)),
        sa.Column('customer_contact_email', sa.String(255)),
        sa.Column('customer_contact_phone', sa.String(20)),

        # Notes
        sa.Column('notes', sa.Text),
        sa.Column('customer_notes', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('planning', 'awaiting_deposit', 'in_progress', 'completed', 'on_hold', 'cancelled')",
            name='valid_project_timeline_status'
        ),
        sa.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name='valid_completion_percentage'
        ),
    )

    # Indexes
    op.create_index('idx_project_timelines_quote_id', 'project_timelines', ['quote_id'])
    op.create_index('idx_project_timelines_status', 'project_timelines', ['status'])

    # ========================================================================
    # PROJECT PHASES TABLE
    # ========================================================================
    op.create_table(
        'project_phases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),

        # Phase identification
        sa.Column('phase_name', sa.String(100), nullable=False),
        sa.Column('phase_letter', sa.String(5), nullable=False),
        sa.Column('phase_number', sa.Integer, nullable=False),

        # Phase description
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('deliverables', postgresql.JSON, nullable=False),

        # Pricing
        sa.Column('phase_cost', sa.Numeric(12, 2), nullable=False),
        sa.Column('deposit_required', sa.Numeric(12, 2), nullable=False),
        sa.Column('deposit_percentage', sa.Numeric(5, 2), server_default='50.00'),

        # Hardware breakdown
        sa.Column('hardware_cost', sa.Numeric(12, 2), server_default='0'),
        sa.Column('installation_cost', sa.Numeric(12, 2), server_default='0'),
        sa.Column('monthly_service_cost', sa.Numeric(10, 2), server_default='0'),

        # Timeline
        sa.Column('estimated_duration_days', sa.Integer),
        sa.Column('estimated_start_date', sa.DateTime(timezone=True)),
        sa.Column('estimated_completion_date', sa.DateTime(timezone=True)),
        sa.Column('actual_start_date', sa.DateTime(timezone=True)),
        sa.Column('actual_completion_date', sa.DateTime(timezone=True)),

        # Dependencies
        sa.Column('depends_on_phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='SET NULL')),
        sa.Column('can_start_after_days', sa.Integer, server_default='0'),

        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='planned'),
        sa.Column('deposit_paid', sa.Boolean, server_default='false'),
        sa.Column('deposit_paid_at', sa.DateTime(timezone=True)),
        sa.Column('deposit_amount_paid', sa.Numeric(12, 2), server_default='0'),

        # Payment tracking
        sa.Column('total_paid', sa.Numeric(12, 2), server_default='0'),
        sa.Column('balance_remaining', sa.Numeric(12, 2)),
        sa.Column('payment_terms', sa.String(100)),

        # Priority and grouping
        sa.Column('is_required', sa.Boolean, server_default='true'),
        sa.Column('is_milestone', sa.Boolean, server_default='false'),
        sa.Column('priority_level', sa.Integer, server_default='5'),

        # Contractor integration
        sa.Column('assigned_contractor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contractors.id', ondelete='SET NULL')),
        sa.Column('contractor_status', sa.String(50), server_default='not_assigned'),
        sa.Column('contractor_assigned_at', sa.DateTime(timezone=True)),
        sa.Column('contractor_started_at', sa.DateTime(timezone=True)),
        sa.Column('contractor_completed_at', sa.DateTime(timezone=True)),
        sa.Column('contractor_quote_amount', sa.Numeric(12, 2)),
        sa.Column('contractor_paid_amount', sa.Numeric(12, 2), server_default='0'),
        sa.Column('contractor_balance', sa.Numeric(12, 2)),
        sa.Column('contractor_rating', sa.Numeric(3, 2)),
        sa.Column('contractor_review', sa.Text),
        sa.Column('contractor_on_time', sa.Boolean),

        # Notes
        sa.Column('internal_notes', sa.Text),
        sa.Column('customer_notes', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('planned', 'unlocked', 'in_progress', 'completed', 'on_hold', 'cancelled')",
            name='valid_project_phase_status'
        ),
        sa.CheckConstraint(
            "contractor_status IN ('not_assigned', 'bidding', 'assigned', 'in_progress', 'completed')",
            name='valid_contractor_status'
        ),
        sa.CheckConstraint(
            "deposit_percentage >= 0 AND deposit_percentage <= 100",
            name='valid_deposit_percentage'
        ),
    )

    # Indexes
    op.create_index('idx_project_phases_quote_id', 'project_phases', ['quote_id'])
    op.create_index('idx_project_phases_status', 'project_phases', ['status'])
    op.create_index('idx_project_phases_phase_number', 'project_phases', ['phase_number'])
    op.create_index('idx_project_phases_depends_on', 'project_phases', ['depends_on_phase_id'])
    op.create_index('idx_project_phases_contractor_id', 'project_phases', ['assigned_contractor_id'])
    op.create_index('idx_project_phases_contractor_status', 'project_phases', ['contractor_status'])

    # ========================================================================
    # PROJECT PHASE LINE ITEMS TABLE
    # ========================================================================
    op.create_table(
        'project_phase_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False),

        # Line item details
        sa.Column('line_number', sa.Integer, nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),

        # Pricing
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),

        # Item type
        sa.Column('item_type', sa.String(50)),
        sa.Column('recurring', sa.Boolean, server_default='false'),
        sa.Column('recurring_interval', sa.String(20)),

        # Product details
        sa.Column('vendor_pricing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_pricing.id', ondelete='SET NULL')),
        sa.Column('product_sku', sa.String(100)),
        sa.Column('product_tier', sa.String(50)),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('ordered_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('installed_at', sa.DateTime(timezone=True)),

        # Notes
        sa.Column('notes', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'ordered', 'delivered', 'installed', 'completed', 'cancelled')",
            name='valid_phase_line_item_status'
        ),
    )

    # Indexes
    op.create_index('idx_project_phase_line_items_phase_id', 'project_phase_line_items', ['phase_id'])
    op.create_index('idx_project_phase_line_items_status', 'project_phase_line_items', ['status'])

    # ========================================================================
    # PROJECT PHASE MILESTONES TABLE
    # ========================================================================
    op.create_table(
        'project_phase_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False),

        # Milestone details
        sa.Column('milestone_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('milestone_order', sa.Integer, nullable=False),

        # Timeline
        sa.Column('target_date', sa.DateTime(timezone=True)),
        sa.Column('actual_completion_date', sa.DateTime(timezone=True)),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('completed', sa.Boolean, server_default='false'),
        sa.Column('completed_by', sa.String(255)),

        # Approval
        sa.Column('requires_customer_approval', sa.Boolean, server_default='false'),
        sa.Column('customer_approved', sa.Boolean, server_default='false'),
        sa.Column('customer_approved_at', sa.DateTime(timezone=True)),

        # Blocking issues
        sa.Column('blocked_reason', sa.Text),
        sa.Column('blocked_at', sa.DateTime(timezone=True)),

        # Notes
        sa.Column('notes', sa.Text),
        sa.Column('completion_notes', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'blocked', 'skipped')",
            name='valid_milestone_status'
        ),
    )

    # Indexes
    op.create_index('idx_project_phase_milestones_phase_id', 'project_phase_milestones', ['phase_id'])
    op.create_index('idx_project_phase_milestones_status', 'project_phase_milestones', ['status'])
    op.create_index('idx_project_phase_milestones_order', 'project_phase_milestones', ['milestone_order'])

    # ========================================================================
    # PROJECT DEPOSITS TABLE
    # ========================================================================
    op.create_table(
        'project_deposits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='SET NULL')),

        # Deposit details
        sa.Column('deposit_number', sa.String(50), nullable=False, unique=True),
        sa.Column('deposit_amount', sa.Numeric(12, 2), nullable=False),

        # Payment info
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_reference', sa.String(255)),
        sa.Column('payment_status', sa.String(50), nullable=False, server_default='pending'),

        # Dates
        sa.Column('deposit_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('cleared_date', sa.DateTime(timezone=True)),

        # Phase unlocking
        sa.Column('unlocks_phase', sa.Boolean, server_default='true'),
        sa.Column('phase_unlocked_at', sa.DateTime(timezone=True)),

        # Allocation
        sa.Column('allocated_amount', sa.Numeric(12, 2)),
        sa.Column('allocation_notes', sa.Text),

        # Receipt and documentation
        sa.Column('receipt_number', sa.String(50)),
        sa.Column('receipt_url', sa.String(500)),

        # Notes
        sa.Column('notes', sa.Text),
        sa.Column('internal_notes', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')",
            name='valid_deposit_payment_status'
        ),
    )

    # Indexes
    op.create_index('idx_project_deposits_quote_id', 'project_deposits', ['quote_id'])
    op.create_index('idx_project_deposits_phase_id', 'project_deposits', ['phase_id'])
    op.create_index('idx_project_deposits_payment_status', 'project_deposits', ['payment_status'])
    op.create_index('idx_project_deposits_number', 'project_deposits', ['deposit_number'])

    # ========================================================================
    # CONTRACTOR BIDS TABLE
    # ========================================================================
    op.create_table(
        'contractor_bids',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contractor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contractors.id', ondelete='CASCADE'), nullable=False),

        # Bid details
        sa.Column('bid_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('bid_currency', sa.String(3), server_default='USD'),

        # Timeline bid
        sa.Column('estimated_start_date', sa.DateTime(timezone=True)),
        sa.Column('estimated_completion_date', sa.DateTime(timezone=True)),
        sa.Column('estimated_duration_days', sa.Integer),

        # Bid breakdown
        sa.Column('labor_cost', sa.Numeric(12, 2)),
        sa.Column('material_cost', sa.Numeric(12, 2)),
        sa.Column('equipment_cost', sa.Numeric(12, 2)),
        sa.Column('other_costs', sa.Numeric(12, 2)),

        # Bid details
        sa.Column('scope_of_work', sa.Text),
        sa.Column('exclusions', sa.Text),
        sa.Column('assumptions', sa.Text),
        sa.Column('notes', sa.Text),

        # Payment terms
        sa.Column('payment_schedule', sa.String(100)),
        sa.Column('warranty_period_days', sa.Integer),
        sa.Column('warranty_terms', sa.Text),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='submitted'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('accepted_at', sa.DateTime(timezone=True)),
        sa.Column('rejected_at', sa.DateTime(timezone=True)),

        # Selection
        sa.Column('is_selected', sa.Boolean, server_default='false'),
        sa.Column('selected_by', sa.String(255)),
        sa.Column('rejection_reason', sa.Text),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('submitted', 'under_review', 'accepted', 'rejected', 'withdrawn')",
            name='valid_contractor_bid_status'
        ),
    )

    # Indexes
    op.create_index('idx_contractor_bids_phase_id', 'contractor_bids', ['phase_id'])
    op.create_index('idx_contractor_bids_contractor_id', 'contractor_bids', ['contractor_id'])
    op.create_index('idx_contractor_bids_status', 'contractor_bids', ['status'])
    op.create_index('idx_contractor_bids_is_selected', 'contractor_bids', ['is_selected'])

    # ========================================================================
    # CONTRACTOR PAYMENTS TABLE
    # ========================================================================
    op.create_table(
        'contractor_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contractor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contractors.id', ondelete='CASCADE'), nullable=False),

        # Payment details
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('payment_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_type', sa.String(50), server_default='progress'),

        # Payment method
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_reference', sa.String(255)),

        # Invoice tracking
        sa.Column('invoice_number', sa.String(100)),
        sa.Column('invoice_date', sa.DateTime(timezone=True)),
        sa.Column('invoice_amount', sa.Numeric(12, 2)),
        sa.Column('invoice_url', sa.String(500)),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('scheduled_date', sa.DateTime(timezone=True)),
        sa.Column('paid_date', sa.DateTime(timezone=True)),
        sa.Column('cleared_date', sa.DateTime(timezone=True)),

        # Milestone tracking
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_phase_milestones.id', ondelete='SET NULL')),
        sa.Column('milestone_completion_verified', sa.Boolean, server_default='false'),

        # Retention
        sa.Column('is_retention', sa.Boolean, server_default='false'),
        sa.Column('retention_percentage', sa.Numeric(5, 2)),
        sa.Column('retention_release_date', sa.DateTime(timezone=True)),

        # Notes
        sa.Column('notes', sa.Text),
        sa.Column('internal_notes', sa.Text),

        # Approval
        sa.Column('approved_by', sa.String(255)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'scheduled', 'paid', 'failed', 'cancelled')",
            name='valid_contractor_payment_status'
        ),
        sa.CheckConstraint(
            "payment_type IN ('deposit', 'progress', 'final', 'bonus', 'retention')",
            name='valid_payment_type'
        ),
    )

    # Indexes
    op.create_index('idx_contractor_payments_phase_id', 'contractor_payments', ['phase_id'])
    op.create_index('idx_contractor_payments_contractor_id', 'contractor_payments', ['contractor_id'])
    op.create_index('idx_contractor_payments_status', 'contractor_payments', ['status'])
    op.create_index('idx_contractor_payments_payment_number', 'contractor_payments', ['payment_number'])
    op.create_index('idx_contractor_payments_paid_date', 'contractor_payments', ['paid_date'])


def downgrade():
    # Drop tables in reverse order (foreign key dependencies)
    op.drop_table('contractor_payments')
    op.drop_table('contractor_bids')
    op.drop_table('project_deposits')
    op.drop_table('project_phase_milestones')
    op.drop_table('project_phase_line_items')
    op.drop_table('project_phases')
    op.drop_table('project_timelines')
