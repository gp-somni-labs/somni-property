"""Create labor pricing configuration tables

Revision ID: 029
Revises: 028
Create Date: 2025-11-23 22:30:00

This migration creates tables to configure labor rates and installation times.
Admins can customize pricing through the UI instead of code changes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

# revision identifiers
revision = '029'
down_revision = '028_add_labor_cost_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Labor rate configuration by category
    op.create_table(
        'labor_rates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('category', sa.String(50), nullable=False, unique=True),
        sa.Column('rate_per_hour', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', sa.String(100), nullable=True)
    )

    # Installation time configuration by device category
    op.create_table(
        'installation_times',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('device_category', sa.String(50), nullable=False, unique=True),
        sa.Column('first_unit_hours', sa.Numeric(10, 2), nullable=False),
        sa.Column('additional_unit_hours', sa.Numeric(10, 2), nullable=False),
        sa.Column('labor_category', sa.String(50), nullable=False, server_default='installation'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', sa.String(100), nullable=True)
    )

    # Material costs by device category
    op.create_table(
        'device_materials',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('device_category', sa.String(50), nullable=False),
        sa.Column('material_name', sa.String(100), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('quantity_per_device', sa.Numeric(10, 2), nullable=False),
        sa.Column('cost_per_unit', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', sa.String(100), nullable=True)
    )

    # Seed default labor rates
    op.execute("""
        INSERT INTO labor_rates (category, rate_per_hour, description) VALUES
        ('installation', 85.00, 'Physical installation of devices'),
        ('configuration', 95.00, 'Software and system configuration'),
        ('networking', 100.00, 'Network setup and integration'),
        ('electrical', 110.00, 'Electrical work and wiring'),
        ('testing', 75.00, 'Testing and quality assurance'),
        ('training', 65.00, 'Customer training and documentation'),
        ('project_management', 125.00, 'Project management overhead');
    """)

    # Seed default installation times
    op.execute("""
        INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
        ('smart_lock', 1.5, 0.75, 'installation', 'Smart lock installation and setup'),
        ('thermostat', 1.0, 0.5, 'installation', 'Smart thermostat installation'),
        ('hub', 2.0, 1.0, 'configuration', 'Hub/controller setup and configuration'),
        ('camera', 1.5, 0.75, 'installation', 'Security camera installation'),
        ('doorbell', 1.25, 0.5, 'installation', 'Video doorbell installation'),
        ('sensor', 0.5, 0.25, 'installation', 'Door/window sensor installation'),
        ('switch', 0.75, 0.35, 'electrical', 'Smart switch installation'),
        ('outlet', 0.75, 0.35, 'electrical', 'Smart outlet installation'),
        ('garage_door', 2.0, 1.0, 'installation', 'Garage door opener installation'),
        ('shade', 1.0, 0.5, 'installation', 'Smart shade/blind installation'),
        ('irrigation', 3.0, 1.5, 'installation', 'Smart irrigation controller'),
        ('leak_detector', 0.5, 0.25, 'installation', 'Water leak detector installation'),
        ('smoke_detector', 0.75, 0.35, 'installation', 'Smart smoke detector installation');
    """)

    # Seed default materials
    op.execute("""
        INSERT INTO device_materials (device_category, material_name, unit, quantity_per_device, cost_per_unit) VALUES
        -- Smart Lock Materials
        ('smart_lock', 'Mounting screws', 'set', 1, 2.50),
        ('smart_lock', 'Wire nuts', 'ea', 2, 0.25),

        -- Thermostat Materials
        ('thermostat', 'Wire (18/5)', 'ft', 25, 0.35),
        ('thermostat', 'Mounting plate', 'ea', 1, 3.00),

        -- Hub Materials
        ('hub', 'CAT6 cable', 'ft', 50, 0.25),
        ('hub', 'Ethernet keystone', 'ea', 1, 2.00),
        ('hub', 'Mounting bracket', 'ea', 1, 5.00),

        -- Camera Materials
        ('camera', 'CAT6 cable', 'ft', 75, 0.25),
        ('camera', 'Mounting bracket', 'ea', 1, 8.00),
        ('camera', 'Weatherproof box', 'ea', 1, 12.00),

        -- Doorbell Materials
        ('doorbell', 'Doorbell wire (18/2)', 'ft', 30, 0.20),
        ('doorbell', 'Mounting wedge', 'ea', 1, 5.00),

        -- Sensor Materials
        ('sensor', 'Mounting tape', 'ea', 1, 1.50),

        -- Switch Materials
        ('switch', 'Wire nuts', 'ea', 3, 0.25),
        ('switch', 'Wall plate', 'ea', 1, 2.00),

        -- Outlet Materials
        ('outlet', 'Wire nuts', 'ea', 3, 0.25),
        ('outlet', 'Wall plate', 'ea', 1, 2.00);
    """)


def downgrade():
    op.drop_table('device_materials')
    op.drop_table('installation_times')
    op.drop_table('labor_rates')
