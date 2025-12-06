"""Add labor pricing tables for quote labor estimation

Revision ID: 017_add_labor_pricing_tables
Revises: 016_add_client_type
Create Date: 2025-11-23

Changes:
- Add labor_templates table for predefined labor task templates
- Add quote_labor_items table for labor items in quotes
- Add labor_materials table for materials catalog
- Add labor cost tracking columns to quotes table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision = '017_add_labor_pricing_tables'
down_revision = '016_add_client_type'
branch_labels = None
depends_on = None


def upgrade():
    """Add labor pricing tables"""
    print("=" * 80)
    print("Adding Labor Pricing Tables")
    print("=" * 80)

    # 1. Add labor cost tracking columns to quotes table
    print("\n[1/4] Adding labor cost columns to quotes table...")
    try:
        op.add_column('quotes', sa.Column('total_labor_cost', sa.Numeric(10, 2), server_default='0', nullable=True))
        op.add_column('quotes', sa.Column('total_materials_cost', sa.Numeric(10, 2), server_default='0', nullable=True))
        op.add_column('quotes', sa.Column('total_labor_hours', sa.Numeric(10, 2), server_default='0', nullable=True))
        op.add_column('quotes', sa.Column('project_duration_days', sa.Integer, nullable=True))
        op.add_column('quotes', sa.Column('installation_start_date', sa.DateTime(timezone=True), nullable=True))
        op.add_column('quotes', sa.Column('installation_completion_date', sa.DateTime(timezone=True), nullable=True))
        print("✅ Added labor cost columns to quotes")
    except Exception as e:
        print(f"⚠️  Labor cost columns may already exist: {e}")

    # 2. Create labor_templates table
    print("\n[2/4] Creating labor_templates table...")
    try:
        op.create_table(
            'labor_templates',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),

            # Template identification
            sa.Column('template_name', sa.String(255), nullable=False, unique=True),
            sa.Column('template_code', sa.String(50), unique=True),
            sa.Column('category', sa.String(100), nullable=False),

            # Description
            sa.Column('description', sa.Text, nullable=False),
            sa.Column('detailed_scope', sa.Text),

            # Pricing
            sa.Column('base_hours', sa.Numeric(10, 2), nullable=False),
            sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=False),

            # Scaling factors
            sa.Column('additional_hours_per_unit', sa.Numeric(10, 2), server_default='0'),
            sa.Column('efficiency_factor', sa.Numeric(5, 2), server_default='1.0'),

            # Associations
            sa.Column('applicable_product_categories', JSONB),
            sa.Column('applicable_domains', JSONB),

            # Requirements
            sa.Column('required_skills', JSONB),
            sa.Column('required_certifications', JSONB),

            # Materials
            sa.Column('typical_materials', JSONB),

            # Conditions
            sa.Column('prerequisites', JSONB),
            sa.Column('notes', sa.Text),

            # Auto-inclusion
            sa.Column('auto_include', sa.Boolean, server_default='false'),
            sa.Column('auto_include_conditions', JSONB),

            # Status
            sa.Column('active', sa.Boolean, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
        )

        # Create indexes
        op.create_index('idx_labor_templates_category', 'labor_templates', ['category'])
        op.create_index('idx_labor_templates_active', 'labor_templates', ['active'])
        op.create_index('idx_labor_templates_code', 'labor_templates', ['template_code'])

        print("✅ Created labor_templates table")
    except Exception as e:
        print(f"⚠️  labor_templates table may already exist: {e}")

    # 3. Create quote_labor_items table
    print("\n[3/4] Creating quote_labor_items table...")
    try:
        op.create_table(
            'quote_labor_items',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('quote_id', UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('labor_template_id', UUID(as_uuid=True), sa.ForeignKey('labor_templates.id', ondelete='SET NULL')),

            # Labor details
            sa.Column('line_number', sa.Integer, nullable=False),
            sa.Column('category', sa.String(100), nullable=False),
            sa.Column('task_name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text, nullable=False),
            sa.Column('scope_of_work', sa.Text),

            # Pricing calculation
            sa.Column('estimated_hours', sa.Numeric(10, 2), nullable=False),
            sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=False),
            sa.Column('labor_subtotal', sa.Numeric(10, 2), nullable=False),

            # Quantity/scaling
            sa.Column('quantity', sa.Numeric(10, 2), server_default='1'),
            sa.Column('unit_type', sa.String(50)),

            # Associated products
            sa.Column('associated_product_ids', JSONB),
            sa.Column('associated_device_count', sa.Integer, server_default='0'),

            # Materials
            sa.Column('materials_needed', JSONB),
            sa.Column('materials_cost', sa.Numeric(10, 2), server_default='0'),

            # Total
            sa.Column('total_cost', sa.Numeric(10, 2), nullable=False),

            # Status
            sa.Column('is_auto_calculated', sa.Boolean, server_default='false'),
            sa.Column('is_optional', sa.Boolean, server_default='false'),
            sa.Column('requires_approval', sa.Boolean, server_default='false'),

            # Scheduling
            sa.Column('estimated_start_date', sa.DateTime(timezone=True)),
            sa.Column('estimated_completion_date', sa.DateTime(timezone=True)),
            sa.Column('duration_days', sa.Integer),

            # Notes
            sa.Column('internal_notes', sa.Text),
            sa.Column('customer_notes', sa.Text),

            sa.Column('display_order', sa.Integer, server_default='0'),

            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
        )

        # Create indexes
        op.create_index('idx_quote_labor_items_quote_id', 'quote_labor_items', ['quote_id'])
        op.create_index('idx_quote_labor_items_category', 'quote_labor_items', ['category'])
        op.create_index('idx_quote_labor_items_template_id', 'quote_labor_items', ['labor_template_id'])

        print("✅ Created quote_labor_items table")
    except Exception as e:
        print(f"⚠️  quote_labor_items table may already exist: {e}")

    # 4. Create labor_materials table
    print("\n[4/4] Creating labor_materials table...")
    try:
        op.create_table(
            'labor_materials',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),

            # Material identification
            sa.Column('material_name', sa.String(255), nullable=False),
            sa.Column('material_code', sa.String(50), unique=True),
            sa.Column('category', sa.String(100)),

            # Description
            sa.Column('description', sa.Text),
            sa.Column('specifications', sa.Text),

            # Pricing
            sa.Column('unit_cost', sa.Numeric(10, 2), nullable=False),
            sa.Column('unit_type', sa.String(50), nullable=False),

            # Vendor info
            sa.Column('vendor_name', sa.String(255)),
            sa.Column('vendor_sku', sa.String(100)),
            sa.Column('vendor_url', sa.String(500)),

            # Usage estimates
            sa.Column('typical_quantity_per_install', sa.Numeric(10, 2)),
            sa.Column('wastage_factor', sa.Numeric(5, 2), server_default='1.1'),

            # Stock management
            sa.Column('stock_quantity', sa.Numeric(10, 2), server_default='0'),
            sa.Column('reorder_threshold', sa.Numeric(10, 2), server_default='0'),

            # Status
            sa.Column('active', sa.Boolean, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
        )

        # Create indexes
        op.create_index('idx_labor_materials_category', 'labor_materials', ['category'])
        op.create_index('idx_labor_materials_active', 'labor_materials', ['active'])

        print("✅ Created labor_materials table")
    except Exception as e:
        print(f"⚠️  labor_materials table may already exist: {e}")

    print("\n" + "=" * 80)
    print("✅ Labor pricing tables migration complete!")
    print("=" * 80)


def downgrade():
    """Remove labor pricing tables"""
    print("=" * 80)
    print("Rolling back labor pricing tables")
    print("=" * 80)

    # Drop tables in reverse order
    op.drop_table('labor_materials')
    op.drop_table('quote_labor_items')
    op.drop_table('labor_templates')

    # Remove columns from quotes
    op.drop_column('quotes', 'installation_completion_date')
    op.drop_column('quotes', 'installation_start_date')
    op.drop_column('quotes', 'project_duration_days')
    op.drop_column('quotes', 'total_labor_hours')
    op.drop_column('quotes', 'total_materials_cost')
    op.drop_column('quotes', 'total_labor_cost')

    print("✅ Rollback complete")
