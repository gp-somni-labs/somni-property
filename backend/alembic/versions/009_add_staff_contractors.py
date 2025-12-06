"""009_add_staff_contractors

Revision ID: 009_add_staff_contractors
Revises: 008_fix_model_schema_mismatches
Create Date: 2025-11-16 10:00:00.000000

Add staff and contractors tables for resource management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_add_staff_contractors'
down_revision = '008_fix_schema_mismatches'
branch_labels = None
depends_on = None


def upgrade():
    """Add staff and contractors tables"""

    # Drop the old contractors table from 001_initial_schema if it exists
    # (this was a simpler version and we're replacing with enhanced version)
    op.execute("DROP TABLE IF EXISTS contractors CASCADE")

    # ========================================================================
    # STAFF TABLE
    # ========================================================================
    op.create_table(
        'staff',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Personal Information
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('phone', sa.String(50)),

        # Employment
        sa.Column('position', sa.String(100), nullable=False),
        sa.Column('department', sa.String(100)),
        sa.Column('employee_id', sa.String(50), unique=True),
        sa.Column('hire_date', sa.Date()),
        sa.Column('employment_status', sa.String(50), server_default='active'),

        # Skills & Certifications
        sa.Column('skills', postgresql.JSONB(), server_default='[]'),
        sa.Column('certifications', postgresql.JSONB(), server_default='[]'),
        sa.Column('hourly_rate', sa.Numeric(10, 2)),

        # Availability
        sa.Column('available', sa.Boolean(), server_default='true'),
        sa.Column('availability_schedule', postgresql.JSONB()),
        sa.Column('current_workload', sa.Integer(), server_default='0'),
        sa.Column('max_concurrent_jobs', sa.Integer(), server_default='5'),

        # Properties Coverage
        sa.Column('assigned_properties', postgresql.JSONB(), server_default='[]'),

        # Performance Metrics
        sa.Column('total_jobs_completed', sa.Integer(), server_default='0'),
        sa.Column('average_rating', sa.Numeric(3, 2)),
        sa.Column('completion_time_avg_hours', sa.Numeric(10, 2)),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime(timezone=True))
    )

    # Staff check constraints
    op.create_check_constraint(
        'valid_employment_status',
        'staff',
        "employment_status IN ('active', 'on_leave', 'terminated')"
    )

    # Staff indexes
    op.create_index('idx_staff_position', 'staff', ['position'])
    op.create_index('idx_staff_status', 'staff', ['employment_status'])
    op.create_index('idx_staff_skills', 'staff', ['skills'], postgresql_using='gin')
    op.create_index('idx_staff_available', 'staff', ['available'], postgresql_where='available = true')
    op.create_index('idx_staff_email', 'staff', ['email'])

    # ========================================================================
    # CONTRACTORS TABLE
    # ========================================================================
    op.create_table(
        'contractors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Business Information
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50), nullable=False),
        sa.Column('secondary_phone', sa.String(50)),
        sa.Column('website', sa.String(255)),

        # Address
        sa.Column('address_line1', sa.String(255)),
        sa.Column('address_line2', sa.String(255)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(50)),
        sa.Column('zip_code', sa.String(20)),

        # Business Details
        sa.Column('business_type', sa.String(100)),
        sa.Column('tax_id', sa.String(50)),
        sa.Column('license_number', sa.String(100)),
        sa.Column('insurance_provider', sa.String(255)),
        sa.Column('insurance_policy_number', sa.String(100)),
        sa.Column('insurance_expires_at', sa.Date()),

        # Service Categories
        sa.Column('categories', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('specialty_services', postgresql.JSONB(), server_default='[]'),

        # Pricing
        sa.Column('pricing_model', sa.String(50), server_default='hourly'),
        sa.Column('hourly_rate', sa.Numeric(10, 2)),
        sa.Column('emergency_rate', sa.Numeric(10, 2)),
        sa.Column('minimum_charge', sa.Numeric(10, 2)),
        sa.Column('travel_fee', sa.Numeric(10, 2)),

        # Availability
        sa.Column('available', sa.Boolean(), server_default='true'),
        sa.Column('available_weekdays', sa.Boolean(), server_default='true'),
        sa.Column('available_weekends', sa.Boolean(), server_default='false'),
        sa.Column('available_24_7', sa.Boolean(), server_default='false'),
        sa.Column('service_area_radius_miles', sa.Integer()),

        # Service Area (geographic coverage)
        sa.Column('service_area_cities', postgresql.JSONB(), server_default='[]'),

        # Approval & Status
        sa.Column('approval_status', sa.String(50), server_default='pending'),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),

        # Performance Metrics
        sa.Column('total_jobs_completed', sa.Integer(), server_default='0'),
        sa.Column('average_rating', sa.Numeric(3, 2)),
        sa.Column('on_time_rate', sa.Numeric(5, 2)),
        sa.Column('response_time_hours', sa.Integer()),
        sa.Column('last_job_date', sa.Date()),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_contact_at', sa.DateTime(timezone=True))
    )

    # Contractors check constraints
    op.create_check_constraint(
        'valid_approval_status',
        'contractors',
        "approval_status IN ('pending', 'approved', 'rejected', 'inactive')"
    )

    op.create_check_constraint(
        'valid_pricing_model',
        'contractors',
        "pricing_model IN ('hourly', 'flat_rate', 'quote_based')"
    )

    # Contractors indexes
    op.create_index('idx_contractors_approval_status', 'contractors', ['approval_status'])
    op.create_index('idx_contractors_available', 'contractors', ['available'], postgresql_where='available = true')
    op.create_index('idx_contractors_categories', 'contractors', ['categories'], postgresql_using='gin')
    op.create_index('idx_contractors_rating', 'contractors', ['average_rating'])
    op.create_index('idx_contractors_email', 'contractors', ['email'])
    op.create_index('idx_contractors_phone', 'contractors', ['phone'])

    # ========================================================================
    # CONTRACTOR QUOTES TABLE
    # ========================================================================
    op.create_table(
        'contractor_quotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('work_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contractor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contractors.id', ondelete='SET NULL')),

        # Quote Details
        sa.Column('contractor_name', sa.String(255), nullable=False),
        sa.Column('contractor_email', sa.String(255)),
        sa.Column('contractor_phone', sa.String(50)),
        sa.Column('quoted_amount', sa.Numeric(10, 2)),
        sa.Column('quote_breakdown', postgresql.JSONB()),

        # Timeline
        sa.Column('availability_date', sa.Date()),
        sa.Column('estimated_completion_date', sa.Date()),
        sa.Column('valid_until', sa.Date()),

        # Status & Source
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('quote_method', sa.String(50)),  # 'manual', 'email', 'api', 'yelp', 'google'
        sa.Column('source_data', postgresql.JSONB()),

        # AI Analysis
        sa.Column('ai_recommendation', postgresql.JSONB()),
        sa.Column('ai_risk_score', sa.Numeric(5, 2)),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('accepted_at', sa.DateTime(timezone=True)),
        sa.Column('rejected_at', sa.DateTime(timezone=True)),
    )

    # Contractor quotes check constraints
    op.create_check_constraint(
        'valid_quote_status',
        'contractor_quotes',
        "status IN ('pending', 'accepted', 'rejected', 'expired', 'withdrawn')"
    )

    op.create_check_constraint(
        'valid_quote_method',
        'contractor_quotes',
        "quote_method IN ('manual', 'email', 'api', 'yelp', 'google', 'angi', 'thumbtack')"
    )

    # Contractor quotes indexes
    op.create_index('idx_contractor_quotes_work_order', 'contractor_quotes', ['work_order_id'])
    op.create_index('idx_contractor_quotes_contractor', 'contractor_quotes', ['contractor_id'])
    op.create_index('idx_contractor_quotes_status', 'contractor_quotes', ['status'])


def downgrade():
    """Remove staff and contractors tables"""

    # Drop contractor_quotes table
    op.drop_index('idx_contractor_quotes_status', table_name='contractor_quotes')
    op.drop_index('idx_contractor_quotes_contractor', table_name='contractor_quotes')
    op.drop_index('idx_contractor_quotes_work_order', table_name='contractor_quotes')
    op.drop_constraint('valid_quote_method', 'contractor_quotes', type_='check')
    op.drop_constraint('valid_quote_status', 'contractor_quotes', type_='check')
    op.drop_table('contractor_quotes')

    # Drop contractors table
    op.drop_index('idx_contractors_phone', table_name='contractors')
    op.drop_index('idx_contractors_email', table_name='contractors')
    op.drop_index('idx_contractors_rating', table_name='contractors')
    op.drop_index('idx_contractors_categories', table_name='contractors')
    op.drop_index('idx_contractors_available', table_name='contractors')
    op.drop_index('idx_contractors_approval_status', table_name='contractors')
    op.drop_constraint('valid_pricing_model', 'contractors', type_='check')
    op.drop_constraint('valid_approval_status', 'contractors', type_='check')
    op.drop_table('contractors')

    # Drop staff table
    op.drop_index('idx_staff_email', table_name='staff')
    op.drop_index('idx_staff_available', table_name='staff')
    op.drop_index('idx_staff_skills', table_name='staff')
    op.drop_index('idx_staff_status', table_name='staff')
    op.drop_index('idx_staff_position', table_name='staff')
    op.drop_constraint('valid_employment_status', 'staff', type_='check')
    op.drop_table('staff')
