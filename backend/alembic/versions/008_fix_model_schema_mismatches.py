"""Fix model/database schema mismatches

Revision ID: 008_fix_schema_mismatches
Revises: 007_add_ai_assistant
Create Date: 2025-11-01

Adds missing columns to units and smart_devices tables to match model definitions.

Units table missing columns:
- monthly_rent (Numeric) - rename from rent_amount
- has_washer_dryer (Boolean)
- has_dishwasher (Boolean)
- has_ac (Boolean)
- has_balcony (Boolean)
- smart_lock_entity_id (String)
- thermostat_entity_id (String)
- energy_sensor_entity_id (String)
- water_sensor_entity_id (String)
- occupancy_sensor_entity_id (String)

SmartDevices table missing columns:
- retired_date (Date)
- retirement_reason (Text)
- location_description (Text)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_fix_schema_mismatches'
down_revision = '007_add_ai_assistant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # 1. Fix Units table
    # ========================================================================

    # Rename rent_amount to monthly_rent for consistency with model
    op.alter_column('units', 'rent_amount', new_column_name='monthly_rent')

    # Add missing boolean amenity fields
    op.add_column('units', sa.Column('has_washer_dryer', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('units', sa.Column('has_dishwasher', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('units', sa.Column('has_ac', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('units', sa.Column('has_balcony', sa.Boolean(), server_default='false', nullable=False))

    # Add smart home entity ID fields
    op.add_column('units', sa.Column('smart_lock_entity_id', sa.String(length=255), nullable=True))
    op.add_column('units', sa.Column('thermostat_entity_id', sa.String(length=255), nullable=True))
    op.add_column('units', sa.Column('energy_sensor_entity_id', sa.String(length=255), nullable=True))
    op.add_column('units', sa.Column('water_sensor_entity_id', sa.String(length=255), nullable=True))
    op.add_column('units', sa.Column('occupancy_sensor_entity_id', sa.String(length=255), nullable=True))

    # ========================================================================
    # 2. Fix SmartDevices table
    # ========================================================================

    # Add retirement tracking fields
    op.add_column('smart_devices', sa.Column('retired_date', sa.Date(), nullable=True))
    op.add_column('smart_devices', sa.Column('retirement_reason', sa.Text(), nullable=True))
    op.add_column('smart_devices', sa.Column('location_description', sa.Text(), nullable=True))


def downgrade() -> None:
    # ========================================================================
    # Reverse SmartDevices changes
    # ========================================================================
    op.drop_column('smart_devices', 'location_description')
    op.drop_column('smart_devices', 'retirement_reason')
    op.drop_column('smart_devices', 'retired_date')

    # ========================================================================
    # Reverse Units changes
    # ========================================================================
    op.drop_column('units', 'occupancy_sensor_entity_id')
    op.drop_column('units', 'water_sensor_entity_id')
    op.drop_column('units', 'energy_sensor_entity_id')
    op.drop_column('units', 'thermostat_entity_id')
    op.drop_column('units', 'smart_lock_entity_id')
    op.drop_column('units', 'has_balcony')
    op.drop_column('units', 'has_ac')
    op.drop_column('units', 'has_dishwasher')
    op.drop_column('units', 'has_washer_dryer')

    # Rename back to rent_amount
    op.alter_column('units', 'monthly_rent', new_column_name='rent_amount')
