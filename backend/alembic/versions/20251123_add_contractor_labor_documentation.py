"""Add comprehensive contractor labor documentation system

Revision ID: 20251123_contractor_labor_docs
Revises: 20251121_0327-939ef182bbe1_merge_disclaimers_and_components
Create Date: 2025-11-23

This migration adds comprehensive contractor labor documentation capabilities including:
- Photo documentation (before/after, progress, issues, safety)
- Contractor notes and communication threads
- Time tracking with GPS verification
- Materials usage tracking with variance analysis
- Before/after photo pairs for showcasing work
- Contractor work examples portfolio
- Complete audit trail and history tracking

Tables Created:
1. quote_labor_item_photos - Photo documentation for labor tasks
2. quote_labor_item_notes - Contractor communication and updates
3. quote_labor_time_entries - Time tracking with GPS verification
4. quote_labor_materials_used - Actual materials vs estimated
5. quote_labor_item_history - Complete audit trail
6. quote_labor_before_after_pairs - Side-by-side comparisons
7. contractor_work_examples - Portfolio/reference library

Enhancements to Existing Tables:
- quote_labor_items: Add contractor assignment, work status, actual tracking, QC fields
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20251123_contractor_labor_docs'
down_revision = '939ef182bbe1'
branch_labels = None
depends_on = None


def upgrade():
    """Add contractor labor documentation tables and enhance quote_labor_items"""

    # ============================================================================
    # 1. ENHANCE EXISTING quote_labor_items TABLE
    # ============================================================================

    # Contractor assignment
    op.add_column('quote_labor_items', sa.Column('assigned_contractor_id', UUID(as_uuid=True), nullable=True))
    op.add_column('quote_labor_items', sa.Column('contractor_assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quote_labor_items', sa.Column('contractor_assigned_by', sa.String(255), nullable=True))

    # Work status tracking
    op.add_column('quote_labor_items', sa.Column('work_status', sa.String(50), server_default='pending'))
    op.add_column('quote_labor_items', sa.Column('work_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quote_labor_items', sa.Column('work_completed_at', sa.DateTime(timezone=True), nullable=True))

    # Actual time tracking
    op.add_column('quote_labor_items', sa.Column('actual_hours', sa.Numeric(10, 2), nullable=True))
    op.add_column('quote_labor_items', sa.Column('actual_labor_cost', sa.Numeric(10, 2), nullable=True))
    op.add_column('quote_labor_items', sa.Column('actual_materials_cost', sa.Numeric(10, 2), nullable=True))
    op.add_column('quote_labor_items', sa.Column('actual_total_cost', sa.Numeric(10, 2), nullable=True))

    # Variance tracking
    op.add_column('quote_labor_items', sa.Column('hours_variance', sa.Numeric(10, 2), nullable=True))
    op.add_column('quote_labor_items', sa.Column('cost_variance', sa.Numeric(10, 2), nullable=True))

    # Customer approval
    op.add_column('quote_labor_items', sa.Column('requires_customer_approval', sa.Boolean(), server_default='false'))
    op.add_column('quote_labor_items', sa.Column('customer_approved', sa.Boolean(), nullable=True))
    op.add_column('quote_labor_items', sa.Column('customer_approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quote_labor_items', sa.Column('customer_approval_notes', sa.Text(), nullable=True))

    # Quality control
    op.add_column('quote_labor_items', sa.Column('qc_passed', sa.Boolean(), nullable=True))
    op.add_column('quote_labor_items', sa.Column('qc_performed_by', sa.String(255), nullable=True))
    op.add_column('quote_labor_items', sa.Column('qc_performed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quote_labor_items', sa.Column('qc_notes', sa.Text(), nullable=True))

    # Location tracking
    op.execute(text("ALTER TABLE quote_labor_items ADD COLUMN work_location_coords POINT"))
    op.add_column('quote_labor_items', sa.Column('work_location_address', sa.Text(), nullable=True))

    # Equipment/tools used
    op.add_column('quote_labor_items', sa.Column('equipment_used', JSONB, server_default=text("'[]'::jsonb")))

    # Additional metadata
    op.add_column('quote_labor_items', sa.Column('weather_conditions', sa.Text(), nullable=True))
    op.add_column('quote_labor_items', sa.Column('access_notes', sa.Text(), nullable=True))
    op.add_column('quote_labor_items', sa.Column('safety_notes', sa.Text(), nullable=True))

    # Create foreign key constraint for contractor
    op.create_foreign_key(
        'fk_quote_labor_items_contractor',
        'quote_labor_items', 'contractors',
        ['assigned_contractor_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create indexes
    op.create_index('idx_quote_labor_contractor', 'quote_labor_items', ['assigned_contractor_id'])
    op.create_index('idx_quote_labor_status', 'quote_labor_items', ['work_status'])
    op.create_index('idx_quote_labor_dates', 'quote_labor_items', ['work_started_at', 'work_completed_at'])

    # Add check constraint for work_status
    op.create_check_constraint(
        'valid_work_status',
        'quote_labor_items',
        "work_status IN ('pending', 'assigned', 'in_progress', 'completed', 'on_hold', 'cancelled', 'needs_review')"
    )

    # ============================================================================
    # 2. CREATE quote_labor_item_photos TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_item_photos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Photo metadata
        sa.Column('photo_type', sa.String(50), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),

        # Photo details
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('photo_taken_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('photo_taken_by', sa.String(255), nullable=True),
        sa.Column('photographer_type', sa.String(50), nullable=True),

        # Location metadata
        sa.Column('location_notes', sa.Text(), nullable=True),

        # Categorization
        sa.Column('tags', JSONB, server_default=text("'[]'::jsonb")),
        sa.Column('related_task', sa.String(255), nullable=True),

        # Analysis/annotations
        sa.Column('annotations', JSONB, server_default=text("'[]'::jsonb")),
        sa.Column('ai_analysis', JSONB, nullable=True),

        # Display settings
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('show_to_customer', sa.Boolean(), server_default='true'),
        sa.Column('show_in_pdf', sa.Boolean(), server_default='true'),
        sa.Column('is_thumbnail', sa.Boolean(), server_default='false'),

        # Quality/review
        sa.Column('approved_for_display', sa.Boolean(), server_default='true'),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE')
    )

    # Add GPS coordinates column separately (PostGIS POINT type)
    op.execute(text("ALTER TABLE quote_labor_item_photos ADD COLUMN gps_coordinates POINT"))

    # Create indexes
    op.create_index('idx_labor_photos_item_id', 'quote_labor_item_photos', ['labor_item_id'])
    op.create_index('idx_labor_photos_type', 'quote_labor_item_photos', ['photo_type'])
    op.create_index('idx_labor_photos_taken_at', 'quote_labor_item_photos', ['photo_taken_at'])
    op.create_index('idx_labor_photos_display_order', 'quote_labor_item_photos', ['labor_item_id', 'display_order'])

    # ============================================================================
    # 3. CREATE quote_labor_item_notes TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_item_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Note content
        sa.Column('note_type', sa.String(50), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('note_title', sa.String(255), nullable=True),

        # Attribution
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_by_type', sa.String(50), nullable=False),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),

        # Visibility
        sa.Column('is_internal', sa.Boolean(), server_default='false'),
        sa.Column('show_to_customer', sa.Boolean(), server_default='true'),
        sa.Column('requires_response', sa.Boolean(), server_default='false'),

        # Response/resolution
        sa.Column('responded_to', sa.Boolean(), server_default='false'),
        sa.Column('responded_by', sa.String(255), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),

        # Categorization
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('tags', JSONB, server_default=text("'[]'::jsonb")),

        # Attachments
        sa.Column('attached_photo_ids', JSONB, server_default=text("'[]'::jsonb")),
        sa.Column('attached_files', JSONB, server_default=text("'[]'::jsonb")),

        # Time tracking
        sa.Column('hours_worked', sa.Numeric(10, 2), nullable=True),
        sa.Column('work_date', sa.Date(), nullable=True),

        # Location
        sa.Column('location_name', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE')
    )

    # Add GPS coordinates column
    op.execute(text("ALTER TABLE quote_labor_item_notes ADD COLUMN location_coords POINT"))

    # Create indexes
    op.create_index('idx_labor_notes_item_id', 'quote_labor_item_notes', ['labor_item_id'])
    op.create_index('idx_labor_notes_type', 'quote_labor_item_notes', ['note_type'])
    op.create_index('idx_labor_notes_created_at', 'quote_labor_item_notes', ['created_at'])

    # ============================================================================
    # 4. CREATE quote_labor_time_entries TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_time_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Time details
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('duration_hours', sa.Numeric(10, 2), nullable=False),

        # Worker info
        sa.Column('contractor_id', UUID(as_uuid=True), nullable=True),
        sa.Column('worker_name', sa.String(255), nullable=False),
        sa.Column('worker_role', sa.String(100), nullable=True),

        # Work performed
        sa.Column('work_description', sa.Text(), nullable=True),
        sa.Column('tasks_completed', JSONB, server_default=text("'[]'::jsonb")),

        # Billing
        sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('billable', sa.Boolean(), server_default='true'),
        sa.Column('approved', sa.Boolean(), server_default='false'),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        # Location verification
        sa.Column('verified', sa.Boolean(), server_default='false'),

        # Break time
        sa.Column('break_duration_hours', sa.Numeric(10, 2), server_default='0'),

        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('issues_encountered', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], ondelete='SET NULL')
    )

    # Add GPS coordinates columns
    op.execute(text("ALTER TABLE quote_labor_time_entries ADD COLUMN clock_in_location POINT"))
    op.execute(text("ALTER TABLE quote_labor_time_entries ADD COLUMN clock_out_location POINT"))

    # Create indexes
    op.create_index('idx_labor_time_item_id', 'quote_labor_time_entries', ['labor_item_id'])
    op.create_index('idx_labor_time_contractor', 'quote_labor_time_entries', ['contractor_id'])
    op.create_index('idx_labor_time_date', 'quote_labor_time_entries', ['work_date'])
    op.create_index('idx_labor_time_approved', 'quote_labor_time_entries', ['approved'])

    # ============================================================================
    # 5. CREATE quote_labor_materials_used TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_materials_used',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Material details
        sa.Column('material_name', sa.String(255), nullable=False),
        sa.Column('material_category', sa.String(100), nullable=True),
        sa.Column('quantity_used', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_type', sa.String(50), nullable=False),

        # Pricing
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_cost', sa.Numeric(10, 2), nullable=True),

        # Vendor/source
        sa.Column('vendor_name', sa.String(255), nullable=True),
        sa.Column('purchase_order_number', sa.String(100), nullable=True),
        sa.Column('receipt_photo_url', sa.Text(), nullable=True),

        # Tracking
        sa.Column('used_date', sa.Date(), nullable=True),
        sa.Column('recorded_by', sa.String(255), nullable=True),

        # Comparison to estimate
        sa.Column('was_estimated', sa.Boolean(), server_default='false'),
        sa.Column('estimated_quantity', sa.Numeric(10, 2), nullable=True),
        sa.Column('quantity_variance', sa.Numeric(10, 2), nullable=True),

        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reason_for_variance', sa.Text(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('idx_labor_materials_item_id', 'quote_labor_materials_used', ['labor_item_id'])
    op.create_index('idx_labor_materials_category', 'quote_labor_materials_used', ['material_category'])
    op.create_index('idx_labor_materials_date', 'quote_labor_materials_used', ['used_date'])

    # ============================================================================
    # 6. CREATE quote_labor_item_history TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_item_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Change tracking
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),

        # Change details
        sa.Column('changed_by', sa.String(255), nullable=True),
        sa.Column('changed_by_type', sa.String(50), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),

        # Metadata
        sa.Column('metadata', JSONB, server_default=text("'{}'::jsonb")),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('idx_labor_history_item_id', 'quote_labor_item_history', ['labor_item_id'])
    op.create_index('idx_labor_history_type', 'quote_labor_item_history', ['change_type'])
    op.create_index('idx_labor_history_created_at', 'quote_labor_item_history', ['created_at'])

    # ============================================================================
    # 7. CREATE quote_labor_before_after_pairs TABLE
    # ============================================================================

    op.create_table(
        'quote_labor_before_after_pairs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('labor_item_id', UUID(as_uuid=True), nullable=False),

        # Photo references
        sa.Column('before_photo_id', UUID(as_uuid=True), nullable=True),
        sa.Column('after_photo_id', UUID(as_uuid=True), nullable=True),

        # Comparison details
        sa.Column('pair_title', sa.String(255), nullable=True),
        sa.Column('pair_description', sa.Text(), nullable=True),
        sa.Column('work_performed', sa.Text(), nullable=True),

        # Metrics/measurements
        sa.Column('before_measurement', sa.Numeric(10, 2), nullable=True),
        sa.Column('after_measurement', sa.Numeric(10, 2), nullable=True),
        sa.Column('improvement_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('measurement_unit', sa.String(50), nullable=True),

        # Display
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('show_to_customer', sa.Boolean(), server_default='true'),
        sa.Column('featured', sa.Boolean(), server_default='false'),

        # Annotations
        sa.Column('before_annotations', JSONB, nullable=True),
        sa.Column('after_annotations', JSONB, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.ForeignKeyConstraint(['labor_item_id'], ['quote_labor_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['before_photo_id'], ['quote_labor_item_photos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['after_photo_id'], ['quote_labor_item_photos.id'], ondelete='SET NULL')
    )

    # Create indexes
    op.create_index('idx_before_after_item_id', 'quote_labor_before_after_pairs', ['labor_item_id'])
    op.create_index('idx_before_after_display_order', 'quote_labor_before_after_pairs', ['labor_item_id', 'display_order'])

    # ============================================================================
    # 8. CREATE contractor_work_examples TABLE
    # ============================================================================

    op.create_table(
        'contractor_work_examples',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()')),
        sa.Column('contractor_id', UUID(as_uuid=True), nullable=True),

        # Example details
        sa.Column('example_title', sa.String(255), nullable=False),
        sa.Column('example_description', sa.Text(), nullable=True),
        sa.Column('work_category', sa.String(100), nullable=True),
        sa.Column('difficulty_level', sa.String(50), nullable=True),

        # Photos
        sa.Column('primary_photo_url', sa.Text(), nullable=False),
        sa.Column('additional_photos', JSONB, server_default=text("'[]'::jsonb")),

        # Project details
        sa.Column('project_type', sa.String(100), nullable=True),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Numeric(10, 2), nullable=True),

        # Skills showcased
        sa.Column('skills_demonstrated', JSONB, server_default=text("'[]'::jsonb")),
        sa.Column('equipment_used', JSONB, server_default=text("'[]'::jsonb")),

        # Customer info
        sa.Column('customer_satisfaction_rating', sa.Integer(), nullable=True),
        sa.Column('customer_testimonial', sa.Text(), nullable=True),

        # Display settings
        sa.Column('is_public', sa.Boolean(), server_default='true'),
        sa.Column('show_in_portfolio', sa.Boolean(), server_default='true'),
        sa.Column('display_order', sa.Integer(), server_default='0'),

        # Quality
        sa.Column('approved', sa.Boolean(), server_default='false'),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('idx_work_examples_contractor', 'contractor_work_examples', ['contractor_id'])
    op.create_index('idx_work_examples_category', 'contractor_work_examples', ['work_category'])

    print("✅ Contractor labor documentation tables created successfully")


def downgrade():
    """Remove contractor labor documentation tables and columns"""

    # Drop tables in reverse order
    op.drop_table('contractor_work_examples')
    op.drop_table('quote_labor_before_after_pairs')
    op.drop_table('quote_labor_item_history')
    op.drop_table('quote_labor_materials_used')
    op.drop_table('quote_labor_time_entries')
    op.drop_table('quote_labor_item_notes')
    op.drop_table('quote_labor_item_photos')

    # Drop columns from quote_labor_items
    op.drop_constraint('valid_work_status', 'quote_labor_items', type_='check')
    op.drop_index('idx_quote_labor_dates', table_name='quote_labor_items')
    op.drop_index('idx_quote_labor_status', table_name='quote_labor_items')
    op.drop_index('idx_quote_labor_contractor', table_name='quote_labor_items')
    op.drop_constraint('fk_quote_labor_items_contractor', 'quote_labor_items', type_='foreignkey')

    op.drop_column('quote_labor_items', 'safety_notes')
    op.drop_column('quote_labor_items', 'access_notes')
    op.drop_column('quote_labor_items', 'weather_conditions')
    op.drop_column('quote_labor_items', 'equipment_used')
    op.drop_column('quote_labor_items', 'work_location_address')
    op.execute(text("ALTER TABLE quote_labor_items DROP COLUMN IF EXISTS work_location_coords"))
    op.drop_column('quote_labor_items', 'qc_notes')
    op.drop_column('quote_labor_items', 'qc_performed_at')
    op.drop_column('quote_labor_items', 'qc_performed_by')
    op.drop_column('quote_labor_items', 'qc_passed')
    op.drop_column('quote_labor_items', 'customer_approval_notes')
    op.drop_column('quote_labor_items', 'customer_approved_at')
    op.drop_column('quote_labor_items', 'customer_approved')
    op.drop_column('quote_labor_items', 'requires_customer_approval')
    op.drop_column('quote_labor_items', 'cost_variance')
    op.drop_column('quote_labor_items', 'hours_variance')
    op.drop_column('quote_labor_items', 'actual_total_cost')
    op.drop_column('quote_labor_items', 'actual_materials_cost')
    op.drop_column('quote_labor_items', 'actual_labor_cost')
    op.drop_column('quote_labor_items', 'actual_hours')
    op.drop_column('quote_labor_items', 'work_completed_at')
    op.drop_column('quote_labor_items', 'work_started_at')
    op.drop_column('quote_labor_items', 'work_status')
    op.drop_column('quote_labor_items', 'contractor_assigned_by')
    op.drop_column('quote_labor_items', 'contractor_assigned_at')
    op.drop_column('quote_labor_items', 'assigned_contractor_id')

    print("✅ Contractor labor documentation removed successfully")
