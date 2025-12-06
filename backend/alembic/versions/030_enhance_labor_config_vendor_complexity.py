"""Enhance labor configuration with vendor-specific pricing and complexity factors

Revision ID: 030
Revises: 029
Create Date: 2025-11-23 23:00:00

This migration enhances the labor configuration system with:
1. Vendor-specific pricing (different vendors have different installation times)
2. Model-specific pricing (specific models may require more/less time)
3. Complexity factors (neutral vs non-neutral wiring, accessibility, etc.)
4. Contractor-specific labor rates (different contractors charge different rates)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # 1. Enhance installation_times table with vendor/model/complexity
    # ========================================================================

    # Drop the unique constraint on device_category (we need multiple entries per category)
    op.drop_constraint('installation_times_device_category_key', 'installation_times', type_='unique')

    # Add new columns
    op.add_column('installation_times', sa.Column('vendor', sa.String(100), nullable=True))
    op.add_column('installation_times', sa.Column('model', sa.String(100), nullable=True))
    op.add_column('installation_times', sa.Column('complexity_type', sa.String(50), nullable=True))
    op.add_column('installation_times', sa.Column('complexity_multiplier', sa.Numeric(3, 2), nullable=False, server_default='1.00'))
    op.add_column('installation_times', sa.Column('notes', sa.Text, nullable=True))

    # Create new unique index allowing multiple entries per device_category
    # NULL values in vendor/model/complexity_type are treated as distinct
    op.create_index(
        'installation_times_unique_idx',
        'installation_times',
        ['device_category', 'vendor', 'model', 'complexity_type'],
        unique=True,
        postgresql_nulls_not_distinct=False  # Allow multiple NULLs
    )

    # ========================================================================
    # 2. Create contractor_labor_rates table
    # ========================================================================

    op.create_table(
        'contractor_labor_rates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('contractor_id', UUID(as_uuid=True), nullable=False),
        sa.Column('labor_category', sa.String(50), nullable=False),
        sa.Column('rate_per_hour', sa.Numeric(10, 2), nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.UniqueConstraint('contractor_id', 'labor_category', name='contractor_labor_rates_unique')
    )

    # ========================================================================
    # 3. Seed vendor-specific installation times
    # ========================================================================

    # Generic entries already exist from migration 029
    # Now add vendor-specific variations

    # Yale Smart Locks (easier installation, better documentation)
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, model, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('smart_lock', 'Yale', 'Assure Lock 2', 1.25, 0.65, 'installation', 0.90, 'Yale locks have excellent documentation and standardized installation'),
        ('smart_lock', 'Yale', 'Assure Lever', 1.25, 0.65, 'installation', 0.90, 'Lever design, similar to Assure Lock 2')
    """)

    # Schlage Smart Locks (more complex setup)
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, model, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('smart_lock', 'Schlage', 'Encode Plus', 1.75, 0.85, 'installation', 1.10, 'Schlage Encode Plus requires WiFi setup and calibration'),
        ('smart_lock', 'Schlage', 'Sense', 1.60, 0.80, 'installation', 1.05, 'HomeKit setup adds complexity')
    """)

    # August Smart Locks (retrofit, easier but requires calibration)
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, model, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('smart_lock', 'August', 'WiFi Smart Lock', 1.00, 0.50, 'installation', 0.80, 'Retrofit design, no wiring changes needed')
    """)

    # Thermostats - Complexity based on wiring
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, complexity_type, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('thermostat', NULL, 'neutral_wire_present', 0.75, 0.40, 'installation', 0.85, 'C-wire already present, simple swap'),
        ('thermostat', NULL, 'no_neutral_wire', 1.50, 0.75, 'electrical', 1.40, 'Requires running new C-wire or installing power adapter'),
        ('thermostat', NULL, 'heat_only', 0.60, 0.35, 'installation', 0.75, 'Heat-only systems are simpler')
    """)

    # Ecobee Thermostats (specific models)
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, model, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('thermostat', 'Ecobee', 'SmartThermostat', 1.00, 0.50, 'installation', 1.00, 'Standard installation with remote sensors'),
        ('thermostat', 'Ecobee', 'Lite', 0.85, 0.45, 'installation', 0.90, 'No remote sensors, simpler')
    """)

    # Google Nest Thermostats
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, model, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('thermostat', 'Google', 'Nest Learning', 1.10, 0.55, 'installation', 1.05, 'Learning algorithms require initial calibration'),
        ('thermostat', 'Google', 'Nest Thermostat', 0.90, 0.45, 'installation', 0.95, 'Budget model, simpler installation')
    """)

    # Switches - Complexity based on wiring
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, complexity_type, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('switch', NULL, 'neutral_wire_present', 0.60, 0.30, 'electrical', 0.85, 'Neutral wire present, standard installation'),
        ('switch', NULL, 'no_neutral_wire', 1.20, 0.60, 'electrical', 1.50, 'No neutral wire, requires special switch or rewiring'),
        ('switch', NULL, '3way_switch', 1.00, 0.50, 'electrical', 1.25, '3-way switch configuration, more complex wiring')
    """)

    # Cameras - Complexity based on mounting location
    op.execute("""
        INSERT INTO installation_times (device_category, vendor, complexity_type, first_unit_hours, additional_unit_hours, labor_category, complexity_multiplier, description)
        VALUES
        ('camera', NULL, 'easy_access', 1.25, 0.65, 'installation', 0.90, 'Ground floor, easy access, minimal cable run'),
        ('camera', NULL, 'ladder_required', 1.75, 0.90, 'installation', 1.20, 'Requires ladder, 10-15ft height'),
        ('camera', NULL, 'difficult_access', 2.50, 1.25, 'installation', 1.60, 'High ceilings, attic runs, or challenging routing')
    """)

    # ========================================================================
    # 4. Seed vendor-specific materials (optional enhancements)
    # ========================================================================

    # Vendor-specific materials that may be needed
    op.execute("""
        INSERT INTO device_materials (device_category, material_name, unit, quantity_per_device, cost_per_unit)
        VALUES
        ('switch', 'Lutron LUT-MLC adapter (no neutral)', 'ea', 1, 8.50),
        ('thermostat', 'Venstar Add-A-Wire adapter', 'ea', 1, 22.00),
        ('thermostat', 'Ecobee Power Extender Kit', 'ea', 1, 20.00),
        ('camera', 'Cable concealment raceway', 'ft', 15, 1.25),
        ('camera', 'J-box for exterior mounting', 'ea', 1, 8.00)
    """)


def downgrade():
    # Drop contractor_labor_rates table
    op.drop_table('contractor_labor_rates')

    # Drop the new unique index
    op.drop_index('installation_times_unique_idx', table_name='installation_times')

    # Remove new columns from installation_times
    op.drop_column('installation_times', 'notes')
    op.drop_column('installation_times', 'complexity_multiplier')
    op.drop_column('installation_times', 'complexity_type')
    op.drop_column('installation_times', 'model')
    op.drop_column('installation_times', 'vendor')

    # Restore original unique constraint
    op.create_unique_constraint('installation_times_device_category_key', 'installation_times', ['device_category'])
