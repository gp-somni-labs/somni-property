"""Add quote product options, comments, and customer selections

Revision ID: 017_add_quote_enhancements
Revises: 019_client_onboarding_system
Create Date: 2025-11-21 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_add_quote_enhancements'
down_revision = '019_client_onboarding_system'
branch_labels = None
depends_on = None


def upgrade():
    # Create quote_product_options table
    op.create_table(
        'quote_product_options',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_category', sa.String(100), nullable=False),

        # Economy tier
        sa.Column('economy_product_name', sa.String(255)),
        sa.Column('economy_unit_price', sa.Numeric(10, 2)),
        sa.Column('economy_vendor_pricing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_pricing.id', ondelete='SET NULL')),
        sa.Column('economy_description', sa.Text()),

        # Standard tier
        sa.Column('standard_product_name', sa.String(255)),
        sa.Column('standard_unit_price', sa.Numeric(10, 2)),
        sa.Column('standard_vendor_pricing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_pricing.id', ondelete='SET NULL')),
        sa.Column('standard_description', sa.Text()),

        # Premium tier
        sa.Column('premium_product_name', sa.String(255)),
        sa.Column('premium_unit_price', sa.Numeric(10, 2)),
        sa.Column('premium_vendor_pricing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_pricing.id', ondelete='SET NULL')),
        sa.Column('premium_description', sa.Text()),

        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('display_order', sa.Integer(), server_default='0'),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    op.create_index('idx_quote_product_options_quote_id', 'quote_product_options', ['quote_id'])
    op.create_index('idx_quote_product_options_category', 'quote_product_options', ['product_category'])

    # Create quote_comments table
    op.create_table(
        'quote_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quote_line_items.id', ondelete='SET NULL')),
        sa.Column('parent_comment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quote_comments.id', ondelete='CASCADE')),

        sa.Column('comment_text', sa.Text(), nullable=False),
        sa.Column('comment_type', sa.String(50)),  # question, concern, request, response, internal

        # Attribution
        sa.Column('created_by', sa.String(255)),  # Admin username or 'customer'
        sa.Column('created_by_email', sa.String(255)),  # Customer email
        sa.Column('is_internal', sa.Boolean(), server_default='false'),  # Hidden from customer

        # Metadata
        sa.Column('attachments', postgresql.JSONB()),  # File references
        sa.Column('resolved', sa.Boolean(), server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_by', sa.String(255)),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    op.create_index('idx_quote_comments_quote_id', 'quote_comments', ['quote_id'])
    op.create_index('idx_quote_comments_parent', 'quote_comments', ['parent_comment_id'])
    op.create_index('idx_quote_comments_is_internal', 'quote_comments', ['is_internal'])
    op.create_index('idx_quote_comments_created_at', 'quote_comments', ['created_at'])

    # Create quote_customer_selections table
    op.create_table(
        'quote_customer_selections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),

        sa.Column('selected_tier', sa.String(50)),  # economy, standard, premium, custom

        # Custom mix-and-match selections
        sa.Column('custom_selections', postgresql.JSONB()),  # {"smart_locks": "premium", "thermostats": "standard"}

        sa.Column('total_hardware_cost', sa.Numeric(10, 2)),
        sa.Column('total_monthly_cost', sa.Numeric(10, 2)),

        sa.Column('customer_notes', sa.Text()),
        sa.Column('approved', sa.Boolean(), server_default='false'),
        sa.Column('approved_at', sa.DateTime(timezone=True)),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    op.create_index('idx_quote_customer_selections_quote_id', 'quote_customer_selections', ['quote_id'])
    op.create_index('idx_quote_customer_selections_approved', 'quote_customer_selections', ['approved'])

    # Add customer_portal_token column to quotes table
    op.add_column('quotes', sa.Column('customer_portal_token', sa.String(500)))
    op.add_column('quotes', sa.Column('customer_portal_token_expires', sa.DateTime(timezone=True)))

    op.create_index('idx_quotes_portal_token', 'quotes', ['customer_portal_token'])


def downgrade():
    op.drop_index('idx_quotes_portal_token', 'quotes')
    op.drop_column('quotes', 'customer_portal_token_expires')
    op.drop_column('quotes', 'customer_portal_token')

    op.drop_index('idx_quote_customer_selections_approved', 'quote_customer_selections')
    op.drop_index('idx_quote_customer_selections_quote_id', 'quote_customer_selections')
    op.drop_table('quote_customer_selections')

    op.drop_index('idx_quote_comments_created_at', 'quote_comments')
    op.drop_index('idx_quote_comments_is_internal', 'quote_comments')
    op.drop_index('idx_quote_comments_parent', 'quote_comments')
    op.drop_index('idx_quote_comments_quote_id', 'quote_comments')
    op.drop_table('quote_comments')

    op.drop_index('idx_quote_product_options_category', 'quote_product_options')
    op.drop_index('idx_quote_product_options_quote_id', 'quote_product_options')
    op.drop_table('quote_product_options')
