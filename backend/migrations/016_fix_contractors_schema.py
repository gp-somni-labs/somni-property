"""
Migration 016: Fix contractors table schema
Adds missing columns to contractors table to match the Contractor model
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import text


def upgrade():
    """Add missing columns to contractors table"""

    # Check if columns exist before adding them
    conn = op.get_bind()

    # Get existing columns
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'contractors'
    """))
    existing_columns = {row[0] for row in result}

    # Add missing columns if they don't exist
    columns_to_add = {
        'contact_name': sa.Column('contact_name', sa.String(255)),
        'secondary_phone': sa.Column('secondary_phone', sa.String(20)),
        'website': sa.Column('website', sa.String(500)),
        'address_line1': sa.Column('address_line1', sa.String(255)),
        'city': sa.Column('city', sa.String(100)),
        'state': sa.Column('state', sa.String(50)),
        'zip_code': sa.Column('zip_code', sa.String(20)),
        'business_type': sa.Column('business_type', sa.String(100)),
        'license_number': sa.Column('license_number', sa.String(100)),
        'insurance_provider': sa.Column('insurance_provider', sa.String(255)),
        'insurance_policy_number': sa.Column('insurance_policy_number', sa.String(100)),
        'insurance_expires_at': sa.Column('insurance_expires_at', sa.Date),
        'categories': sa.Column('categories', ARRAY(sa.Text), server_default='{}'),
        'specialty_services': sa.Column('specialty_services', ARRAY(sa.Text), server_default='{}'),
        'pricing_model': sa.Column('pricing_model', sa.String(20), server_default='hourly'),
        'hourly_rate': sa.Column('hourly_rate', sa.Numeric(10, 2)),
        'emergency_rate': sa.Column('emergency_rate', sa.Numeric(10, 2)),
        'minimum_charge': sa.Column('minimum_charge', sa.Numeric(10, 2)),
        'travel_fee': sa.Column('travel_fee', sa.Numeric(10, 2)),
        'available_weekdays': sa.Column('available_weekdays', sa.Boolean, server_default='true'),
        'available_weekends': sa.Column('available_weekends', sa.Boolean, server_default='false'),
        'available_24_7': sa.Column('available_24_7', sa.Boolean, server_default='false'),
        'service_area_radius_miles': sa.Column('service_area_radius_miles', sa.Integer),
        'approval_status': sa.Column('approval_status', sa.String(20), server_default='approved'),
        'available': sa.Column('available', sa.Boolean, server_default='true'),
        'is_active': sa.Column('is_active', sa.Boolean, server_default='true'),
        'average_rating': sa.Column('average_rating', sa.Numeric(3, 2), server_default='0'),
        'total_jobs': sa.Column('total_jobs', sa.Integer, server_default='0'),
        'total_jobs_completed': sa.Column('total_jobs_completed', sa.Integer, server_default='0'),
        'on_time_rate': sa.Column('on_time_rate', sa.Numeric(5, 2)),
        'response_time_hours': sa.Column('response_time_hours', sa.Integer),
        'last_job_date': sa.Column('last_job_date', sa.Date),
        'notes': sa.Column('notes', sa.Text),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    }

    for col_name, col_def in columns_to_add.items():
        if col_name not in existing_columns:
            op.add_column('contractors', col_def)

    # Create indexes if they don't exist
    try:
        op.create_index('idx_contractors_approval_status', 'contractors', ['approval_status'])
    except:
        pass  # Index already exists

    try:
        op.create_index('idx_contractors_available', 'contractors', ['available'])
    except:
        pass  # Index already exists

    try:
        op.create_index('idx_contractors_categories', 'contractors', ['categories'], postgresql_using='gin')
    except:
        pass  # Index already exists


def downgrade():
    """Remove added columns from contractors table"""

    # Get existing columns
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'contractors'
    """))
    existing_columns = {row[0] for row in result}

    # Drop indexes
    try:
        op.drop_index('idx_contractors_categories', table_name='contractors')
    except:
        pass

    try:
        op.drop_index('idx_contractors_available', table_name='contractors')
    except:
        pass

    try:
        op.drop_index('idx_contractors_approval_status', table_name='contractors')
    except:
        pass

    # Drop columns if they exist
    columns_to_drop = [
        'contact_name', 'secondary_phone', 'website', 'address_line1', 'city',
        'state', 'zip_code', 'business_type', 'license_number', 'insurance_provider',
        'insurance_policy_number', 'insurance_expires_at', 'categories', 'specialty_services',
        'pricing_model', 'hourly_rate', 'emergency_rate', 'minimum_charge', 'travel_fee',
        'available_weekdays', 'available_weekends', 'available_24_7', 'service_area_radius_miles',
        'approval_status', 'available', 'is_active', 'average_rating', 'total_jobs',
        'total_jobs_completed', 'on_time_rate', 'response_time_hours', 'last_job_date',
        'notes', 'created_at', 'updated_at'
    ]

    for col_name in columns_to_drop:
        if col_name in existing_columns:
            op.drop_column('contractors', col_name)
