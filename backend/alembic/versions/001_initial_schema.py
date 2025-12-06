"""Initial schema - 14 tables with Invoice Ninja integration

Revision ID: 001_initial
Revises:
Create Date: 2025-10-29 02:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from db.types import GUID, INET, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create contractors table
    op.create_table('contractors',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('trade', sa.String(length=100), nullable=True),
    sa.Column('license_number', sa.String(length=100), nullable=True),
    sa.Column('insurance_expiry', sa.Date(), nullable=True),
    sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )

    # Create properties table
    op.create_table('properties',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('address_line1', sa.String(length=255), nullable=False),
    sa.Column('address_line2', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('state', sa.String(length=50), nullable=False),
    sa.Column('zip_code', sa.String(length=20), nullable=False),
    sa.Column('country', sa.String(length=100), nullable=True, server_default='USA'),
    sa.Column('property_type', sa.String(length=50), nullable=False),
    sa.Column('purchase_date', sa.Date(), nullable=True),
    sa.Column('purchase_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('current_value', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('owner_name', sa.String(length=255), nullable=True),
    sa.Column('owner_email', sa.String(length=255), nullable=True),
    sa.Column('owner_phone', sa.String(length=20), nullable=True),
    sa.Column('ha_instance_id', sa.String(length=100), nullable=True),
    sa.Column('tailscale_ip', INET(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("property_type IN ('residential', 'commercial', 'mixed-use')", name='valid_property_type'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_properties_ha_instance', 'properties', ['ha_instance_id'], unique=False)
    op.create_index('idx_properties_owner_email', 'properties', ['owner_email'], unique=False)

    # Create tenants table
    op.create_table('tenants',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('employer', sa.String(length=255), nullable=True),
    sa.Column('employment_status', sa.String(length=50), nullable=True),
    sa.Column('annual_income', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('emergency_contact_name', sa.String(length=255), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
    sa.Column('emergency_contact_relationship', sa.String(length=50), nullable=True),
    sa.Column('move_in_preference', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('auth_user_id', sa.String(length=255), nullable=True),
    sa.Column('portal_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    sa.Column('invoiceninja_client_id', sa.String(length=255), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='applicant'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("status IN ('applicant', 'active', 'former')", name='valid_tenant_status'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('invoiceninja_client_id'),
    sa.UniqueConstraint('stripe_customer_id')
    )
    op.create_index('idx_tenants_auth_user_id', 'tenants', ['auth_user_id'], unique=False)
    op.create_index('idx_tenants_email', 'tenants', ['email'], unique=False)
    op.create_index('idx_tenants_status', 'tenants', ['status'], unique=False)

    # Create automation_rules table
    op.create_table('automation_rules',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('property_id', GUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('trigger_type', sa.String(length=50), nullable=False),
    sa.Column('trigger_conditions', JSONB(), nullable=True),
    sa.Column('action_type', sa.String(length=50), nullable=False),
    sa.Column('action_parameters', JSONB(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
    sa.Column('priority', sa.Integer(), nullable=True, server_default=sa.text('0')),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create buildings table
    op.create_table('buildings',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('property_id', GUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('floors', sa.Integer(), nullable=False, server_default=sa.text('1')),
    sa.Column('total_units', sa.Integer(), nullable=False, server_default=sa.text('0')),
    sa.Column('year_built', sa.Integer(), nullable=True),
    sa.Column('square_feet', sa.Integer(), nullable=True),
    sa.Column('has_central_hvac', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('has_central_water', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('has_elevator', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('has_parking', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('parking_spaces', sa.Integer(), nullable=True, server_default=sa.text('0')),
    sa.Column('mqtt_topic_prefix', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_buildings_property_id', 'buildings', ['property_id'], unique=False)

    # Create units table
    op.create_table('units',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('building_id', GUID(), nullable=False),
    sa.Column('unit_number', sa.String(length=50), nullable=False),
    sa.Column('floor', sa.Integer(), nullable=True),
    sa.Column('unit_type', sa.String(length=50), nullable=False),
    sa.Column('bedrooms', sa.Integer(), nullable=False),
    sa.Column('bathrooms', sa.Numeric(precision=3, scale=1), nullable=False),
    sa.Column('square_feet', sa.Integer(), nullable=True),
    sa.Column('rent_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('security_deposit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='vacant'),
    sa.Column('available_date', sa.Date(), nullable=True),
    sa.Column('amenities', ARRAY(sa.String()), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('mqtt_topic_prefix', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("status IN ('vacant', 'occupied', 'maintenance', 'reserved')", name='valid_unit_status'),
    sa.CheckConstraint("unit_type IN ('apartment', 'condo', 'townhouse', 'single-family', 'studio', 'penthouse')", name='valid_unit_type'),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_units_available_date', 'units', ['available_date'], unique=False)
    op.create_index('idx_units_building_id', 'units', ['building_id'], unique=False)
    op.create_index('idx_units_status', 'units', ['status'], unique=False)

    # Create access_logs table
    op.create_table('access_logs',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('unit_id', GUID(), nullable=False),
    sa.Column('device_id', GUID(), nullable=True),
    sa.Column('person_name', sa.String(length=255), nullable=True),
    sa.Column('access_type', sa.String(length=50), nullable=False),
    sa.Column('access_method', sa.String(length=50), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.CheckConstraint("access_type IN ('entry', 'exit', 'denied', 'alarm')", name='valid_access_type'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_access_logs_timestamp', 'access_logs', ['timestamp'], unique=False)
    op.create_index('idx_access_logs_unit_timestamp', 'access_logs', ['unit_id', 'timestamp'], unique=False)

    # Create iot_devices table
    op.create_table('iot_devices',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('unit_id', GUID(), nullable=True),
    sa.Column('building_id', GUID(), nullable=True),
    sa.Column('device_name', sa.String(length=255), nullable=False),
    sa.Column('device_type', sa.String(length=100), nullable=False),
    sa.Column('entity_id', sa.String(length=255), nullable=False),
    sa.Column('mqtt_topic', sa.String(length=255), nullable=True),
    sa.Column('manufacturer', sa.String(length=100), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('firmware_version', sa.String(length=50), nullable=True),
    sa.Column('ip_address', INET(), nullable=True),
    sa.Column('mac_address', sa.String(length=17), nullable=True),
    sa.Column('is_online', sa.Boolean(), nullable=True, server_default=sa.text('true')),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.Column('battery_level', sa.Integer(), nullable=True),
    sa.Column('configuration', JSONB(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("device_type IN ('lock', 'thermostat', 'camera', 'sensor', 'switch', 'light', 'alarm', 'other')", name='valid_device_type'),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_iot_devices_device_type', 'iot_devices', ['device_type'], unique=False)
    op.create_index('idx_iot_devices_entity_id', 'iot_devices', ['entity_id'], unique=False)
    op.create_index('idx_iot_devices_unit_id', 'iot_devices', ['unit_id'], unique=False)

    # Create leases table
    op.create_table('leases',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('tenant_id', GUID(), nullable=False),
    sa.Column('unit_id', GUID(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('rent_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('security_deposit', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('rent_due_day', sa.Integer(), nullable=True, server_default=sa.text('1')),
    sa.Column('late_fee_amount', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    sa.Column('late_fee_grace_days', sa.Integer(), nullable=True, server_default=sa.text('3')),
    sa.Column('pet_deposit', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    sa.Column('parking_fee', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('lease_document_id', GUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("status IN ('active', 'expired', 'terminated', 'pending')", name='valid_lease_status'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_leases_dates', 'leases', ['start_date', 'end_date'], unique=False)
    op.create_index('idx_leases_status', 'leases', ['status'], unique=False)
    op.create_index('idx_leases_tenant_id', 'leases', ['tenant_id'], unique=False)
    op.create_index('idx_leases_unit_id', 'leases', ['unit_id'], unique=False)

    # Create utility_bills table
    op.create_table('utility_bills',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('unit_id', GUID(), nullable=False),
    sa.Column('utility_type', sa.String(length=50), nullable=False),
    sa.Column('billing_period_start', sa.Date(), nullable=False),
    sa.Column('billing_period_end', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('usage_kwh', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('paid', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('paid_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("utility_type IN ('electricity', 'water', 'gas', 'internet', 'trash', 'sewer', 'other')", name='valid_utility_type'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create work_orders table
    op.create_table('work_orders',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('unit_id', GUID(), nullable=True),
    sa.Column('building_id', GUID(), nullable=True),
    sa.Column('tenant_id', GUID(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('priority', sa.String(length=20), nullable=True, server_default='medium'),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='open'),
    sa.Column('assigned_to', GUID(), nullable=True),
    sa.Column('reported_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('actual_cost', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('tenant_accessible', sa.Boolean(), nullable=True, server_default=sa.text('true')),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("category IN ('plumbing', 'electrical', 'hvac', 'appliance', 'structural', 'pest-control', 'cleaning', 'landscaping', 'security', 'general-maintenance', 'emergency', 'other')", name='valid_work_order_category'),
    sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent', 'emergency')", name='valid_priority'),
    sa.CheckConstraint("status IN ('open', 'in-progress', 'scheduled', 'on-hold', 'completed', 'cancelled')", name='valid_work_order_status'),
    sa.ForeignKeyConstraint(['assigned_to'], ['contractors.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_work_orders_assigned_to', 'work_orders', ['assigned_to'], unique=False)
    op.create_index('idx_work_orders_building_id', 'work_orders', ['building_id'], unique=False)
    op.create_index('idx_work_orders_priority', 'work_orders', ['priority'], unique=False)
    op.create_index('idx_work_orders_status', 'work_orders', ['status'], unique=False)
    op.create_index('idx_work_orders_unit_id', 'work_orders', ['unit_id'], unique=False)

    # Create documents table
    op.create_table('documents',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('document_type', sa.String(length=50), nullable=False),
    sa.Column('property_id', GUID(), nullable=True),
    sa.Column('unit_id', GUID(), nullable=True),
    sa.Column('tenant_id', GUID(), nullable=True),
    sa.Column('lease_id', GUID(), nullable=True),
    sa.Column('work_order_id', GUID(), nullable=True),
    sa.Column('file_path', sa.String(length=500), nullable=True),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=True),
    sa.Column('docuseal_template_id', sa.Integer(), nullable=True),
    sa.Column('docuseal_submission_id', sa.Integer(), nullable=True),
    sa.Column('signing_status', sa.String(length=20), nullable=True, server_default='unsigned'),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('minio_object_key', sa.String(length=500), nullable=True),
    sa.Column('paperless_document_id', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("document_type IN ('lease', 'work-order', 'invoice', 'receipt', 'inspection', 'notice', 'contract', 'photo', 'other')", name='valid_document_type'),
    sa.CheckConstraint("signing_status IN ('unsigned', 'pending', 'signed', 'expired', 'declined')", name='valid_signing_status'),
    sa.ForeignKeyConstraint(['lease_id'], ['leases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create rent_payments table
    op.create_table('rent_payments',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('lease_id', GUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('paid_date', sa.Date(), nullable=True),
    sa.Column('payment_method', sa.String(length=50), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
    sa.Column('late_fee_charged', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    sa.Column('transaction_id', sa.String(length=255), nullable=True),
    sa.Column('invoice_id', sa.Integer(), nullable=True),
    sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_charge_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_invoice_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_status', sa.String(length=50), nullable=True),
    sa.Column('invoiceninja_invoice_id', sa.String(length=255), nullable=True),
    sa.Column('invoiceninja_payment_id', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint("payment_method IN ('stripe', 'check', 'cash', 'ach', 'wire', 'other')", name='valid_payment_method'),
    sa.CheckConstraint("status IN ('pending', 'paid', 'late', 'partial', 'failed', 'refunded', 'processing')", name='valid_payment_status'),
    sa.ForeignKeyConstraint(['lease_id'], ['leases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stripe_payment_intent_id')
    )
    op.create_index('idx_rent_payments_due_date', 'rent_payments', ['due_date'], unique=False)
    op.create_index('idx_rent_payments_lease_id', 'rent_payments', ['lease_id'], unique=False)
    op.create_index('idx_rent_payments_status', 'rent_payments', ['status'], unique=False)
    op.create_index('idx_rent_payments_stripe_payment_intent', 'rent_payments', ['stripe_payment_intent_id'], unique=False)

    # Create sensor_readings table
    op.create_table('sensor_readings',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('device_id', GUID(), nullable=False),
    sa.Column('reading_type', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("reading_type IN ('temperature', 'humidity', 'motion', 'door-state', 'lock-state', 'power-usage', 'water-usage', 'other')", name='valid_reading_type'),
    sa.ForeignKeyConstraint(['device_id'], ['iot_devices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sensor_readings_device_timestamp', 'sensor_readings', ['device_id', 'timestamp'], unique=False)
    op.create_index('idx_sensor_readings_timestamp', 'sensor_readings', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('sensor_readings')
    op.drop_table('rent_payments')
    op.drop_table('documents')
    op.drop_table('work_orders')
    op.drop_table('utility_bills')
    op.drop_table('leases')
    op.drop_table('iot_devices')
    op.drop_table('access_logs')
    op.drop_table('units')
    op.drop_table('buildings')
    op.drop_table('automation_rules')
    op.drop_table('tenants')
    op.drop_table('properties')
    op.drop_table('contractors')
