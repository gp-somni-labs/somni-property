"""Add quote system tables

Revision ID: 018_add_quote_system
Revises: 20251120_merge_heads_for_quotes
Create Date: 2025-11-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_quote_system'
down_revision = '20251120_merge_heads_for_quotes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pricing_tiers table
    op.create_table(
        'pricing_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tier_name', sa.String(100), nullable=False),
        sa.Column('tier_level', sa.Integer(), nullable=False),
        sa.Column('price_per_unit_monthly', sa.Numeric(10, 2), nullable=False),
        sa.Column('min_units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_units', sa.Integer(), nullable=True),
        sa.Column('smart_home_basic_price', sa.Numeric(10, 2), nullable=False, server_default='15.00'),
        sa.Column('smart_home_premium_price', sa.Numeric(10, 2), nullable=False, server_default='35.00'),
        sa.Column('smart_home_enterprise_price', sa.Numeric(10, 2), nullable=False, server_default='75.00'),
        sa.Column('features_included', postgresql.JSONB(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pricing_tiers_tier_level', 'pricing_tiers', ['tier_level'])
    op.create_index('ix_pricing_tiers_active', 'pricing_tiers', ['active'])

    # Create vendor_pricing table
    op.create_table(
        'vendor_pricing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_name', sa.String(255), nullable=False),
        sa.Column('product_category', sa.String(100), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), nullable=True),
        sa.Column('retail_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('wholesale_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('subscription_monthly', sa.Numeric(10, 2), nullable=True),
        sa.Column('subscription_annual', sa.Numeric(10, 2), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=False, server_default='0.5'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendor_pricing_vendor_name', 'vendor_pricing', ['vendor_name'])
    op.create_index('ix_vendor_pricing_product_category', 'vendor_pricing', ['product_category'])
    op.create_index('ix_vendor_pricing_verified', 'vendor_pricing', ['verified'])

    # Create quotes table
    op.create_table(
        'quotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_number', sa.String(50), nullable=False, unique=True),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('customer_phone', sa.String(50), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('total_units', sa.Integer(), nullable=False),
        sa.Column('property_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('smart_home_penetration', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('monthly_property_mgmt', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('monthly_smart_home', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('monthly_additional_fees', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('monthly_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('annual_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('setup_fees', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('draft', 'sent', 'accepted', 'rejected', 'expired')", name='check_quote_status')
    )
    op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
    op.create_index('ix_quotes_customer_email', 'quotes', ['customer_email'])
    op.create_index('ix_quotes_status', 'quotes', ['status'])
    op.create_index('ix_quotes_created_at', 'quotes', ['created_at'])

    # Create quote_line_items table
    op.create_table(
        'quote_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_type', sa.String(50), nullable=False, server_default='unit'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('recurring_period', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.CheckConstraint("recurring_period IN ('monthly', 'annual', 'one-time') OR recurring_period IS NULL", name='check_recurring_period')
    )
    op.create_index('ix_quote_line_items_quote_id', 'quote_line_items', ['quote_id'])

    # Create quote_templates table
    op.create_table(
        'quote_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_units', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('default_smart_home_penetration', sa.Numeric(5, 2), nullable=False, server_default='25.00'),
        sa.Column('default_discount', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('line_items_template', postgresql.JSONB(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quote_templates_active', 'quote_templates', ['active'])


def downgrade() -> None:
    op.drop_table('quote_templates')
    op.drop_table('quote_line_items')
    op.drop_table('quotes')
    op.drop_table('vendor_pricing')
    op.drop_table('pricing_tiers')
