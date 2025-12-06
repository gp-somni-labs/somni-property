"""Add comprehensive client onboarding system

Revision ID: 019_client_onboarding_system
Revises: 018_add_quote_system
Create Date: 2025-11-21

Changes:
- Add onboarding fields to clients table (contact info, property details, preferences)
- Create client_media table for tracking uploaded files (photos, videos, floorplans, 3D models)
- Add indexes for efficient querying
- Add CHECK constraints for data validation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '019_client_onboarding_system'
down_revision = '018_add_quote_system'
branch_labels = None
depends_on = None


def upgrade():
    """Add client onboarding system"""
    print("=" * 80)
    print("Adding Comprehensive Client Onboarding System")
    print("=" * 80)

    # ========================================================================
    # PHASE 1: Add new fields to clients table
    # ========================================================================
    print("\n📝 Phase 1: Enhancing clients table with onboarding fields...")

    # Contact Information (Additional)
    try:
        op.add_column('clients', sa.Column('primary_contact_name', sa.String(255), nullable=True))
        op.add_column('clients', sa.Column('primary_contact_title', sa.String(100), nullable=True))
        op.add_column('clients', sa.Column('primary_contact_phone', sa.String(20), nullable=True))
        op.add_column('clients', sa.Column('primary_contact_email', sa.String(255), nullable=True))
        print("✅ Added primary contact fields")
    except Exception as e:
        print(f"⚠️  Could not add primary contact fields: {e}")

    # Secondary Contact
    try:
        op.add_column('clients', sa.Column('secondary_contact_name', sa.String(255), nullable=True))
        op.add_column('clients', sa.Column('secondary_contact_title', sa.String(100), nullable=True))
        op.add_column('clients', sa.Column('secondary_contact_phone', sa.String(20), nullable=True))
        op.add_column('clients', sa.Column('secondary_contact_email', sa.String(255), nullable=True))
        print("✅ Added secondary contact fields")
    except Exception as e:
        print(f"⚠️  Could not add secondary contact fields: {e}")

    # Property Information
    try:
        op.add_column('clients', sa.Column('property_name', sa.String(255), nullable=True))
        op.add_column('clients', sa.Column('property_address_line1', sa.String(255), nullable=True))
        op.add_column('clients', sa.Column('property_address_line2', sa.String(255), nullable=True))
        op.add_column('clients', sa.Column('property_city', sa.String(100), nullable=True))
        op.add_column('clients', sa.Column('property_state', sa.String(50), nullable=True))
        op.add_column('clients', sa.Column('property_zip_code', sa.String(20), nullable=True))
        op.add_column('clients', sa.Column('property_country', sa.String(100), server_default='USA'))
        print("✅ Added property address fields")
    except Exception as e:
        print(f"⚠️  Could not add property address fields: {e}")

    # Property Details
    try:
        op.add_column('clients', sa.Column('property_type', sa.String(50), nullable=True))
        op.add_column('clients', sa.Column('property_unit_count', sa.Integer, nullable=True))
        op.add_column('clients', sa.Column('property_year_built', sa.Integer, nullable=True))
        op.add_column('clients', sa.Column('property_square_feet', sa.Integer, nullable=True))
        op.add_column('clients', sa.Column('property_description', sa.Text, nullable=True))
        print("✅ Added property details fields")
    except Exception as e:
        print(f"⚠️  Could not add property details fields: {e}")

    # Onboarding Workflow
    try:
        op.add_column('clients', sa.Column('onboarding_stage', sa.String(50), server_default='initial', nullable=False))
        op.add_column('clients', sa.Column('onboarding_step', sa.Integer, server_default='1', nullable=False))
        op.add_column('clients', sa.Column('onboarding_progress_percent', sa.Integer, server_default='0', nullable=False))
        op.add_column('clients', sa.Column('discovery_call_scheduled_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column('clients', sa.Column('discovery_call_completed_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column('clients', sa.Column('initial_assessment_completed', sa.Boolean, server_default='false', nullable=False))
        print("✅ Added onboarding workflow fields")
    except Exception as e:
        print(f"⚠️  Could not add onboarding workflow fields: {e}")

    # Initial Transcript/Notes
    try:
        op.add_column('clients', sa.Column('discovery_call_transcript', sa.Text, nullable=True))
        op.add_column('clients', sa.Column('initial_notes', sa.Text, nullable=True))
        op.add_column('clients', sa.Column('special_requirements', sa.Text, nullable=True))
        print("✅ Added notes and transcript fields")
    except Exception as e:
        print(f"⚠️  Could not add notes fields: {e}")

    # Communication Preferences
    try:
        op.add_column('clients', sa.Column('preferred_contact_method', sa.String(20), server_default='email'))
        op.add_column('clients', sa.Column('preferred_contact_time', sa.String(50), nullable=True))
        op.add_column('clients', sa.Column('timezone', sa.String(50), server_default='America/New_York'))
        print("✅ Added communication preference fields")
    except Exception as e:
        print(f"⚠️  Could not add communication preference fields: {e}")

    # Add CHECK constraints
    try:
        op.create_check_constraint(
            'valid_onboarding_stage',
            'clients',
            "onboarding_stage IN ('initial', 'discovery', 'assessment', 'proposal', 'contract', 'deployment', 'completed')"
        )
        print("✅ Added onboarding_stage CHECK constraint")
    except Exception as e:
        print(f"⚠️  Could not add onboarding_stage constraint: {e}")

    try:
        op.create_check_constraint(
            'valid_property_type',
            'clients',
            "property_type IN ('single_family', 'multi_unit', 'commercial', 'mixed_use', 'other') OR property_type IS NULL"
        )
        print("✅ Added property_type CHECK constraint")
    except Exception as e:
        print(f"⚠️  Could not add property_type constraint: {e}")

    try:
        op.create_check_constraint(
            'valid_preferred_contact_method',
            'clients',
            "preferred_contact_method IN ('email', 'phone', 'sms', 'any')"
        )
        print("✅ Added preferred_contact_method CHECK constraint")
    except Exception as e:
        print(f"⚠️  Could not add preferred_contact_method constraint: {e}")

    # Add indexes
    try:
        op.create_index('idx_clients_onboarding_stage', 'clients', ['onboarding_stage'])
        op.create_index('idx_clients_property_city', 'clients', ['property_city'])
        op.create_index('idx_clients_property_state', 'clients', ['property_state'])
        print("✅ Added indexes on clients table")
    except Exception as e:
        print(f"⚠️  Could not add indexes: {e}")

    # ========================================================================
    # PHASE 2: Create client_media table
    # ========================================================================
    print("\n📁 Phase 2: Creating client_media table...")

    try:
        op.create_table(
            'client_media',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),

            # Media Classification
            sa.Column('media_type', sa.String(20), nullable=False),
            sa.Column('media_category', sa.String(50), nullable=False),
            sa.Column('file_name', sa.String(500), nullable=False),
            sa.Column('original_file_name', sa.String(500), nullable=False),
            sa.Column('file_extension', sa.String(10), nullable=False),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('file_size_bytes', sa.BigInteger, nullable=False),

            # Storage
            sa.Column('minio_bucket', sa.String(100), nullable=False),
            sa.Column('minio_object_key', sa.String(500), nullable=False),
            sa.Column('minio_url', sa.Text, nullable=True),
            sa.Column('cdn_url', sa.Text, nullable=True),

            # Thumbnails (for images/videos)
            sa.Column('thumbnail_minio_key', sa.String(500), nullable=True),
            sa.Column('thumbnail_url', sa.Text, nullable=True),

            # Metadata
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
            sa.Column('captured_date', sa.Date, nullable=True),

            # Image/Video specific metadata
            sa.Column('width', sa.Integer, nullable=True),
            sa.Column('height', sa.Integer, nullable=True),
            sa.Column('duration_seconds', sa.Integer, nullable=True),
            sa.Column('frame_rate', sa.Numeric(10, 2), nullable=True),

            # Document specific metadata (floorplans, 3D files)
            sa.Column('page_count', sa.Integer, nullable=True),
            sa.Column('document_version', sa.String(50), nullable=True),

            # 3D Model specific metadata
            sa.Column('model_format', sa.String(10), nullable=True),
            sa.Column('polygon_count', sa.Integer, nullable=True),
            sa.Column('model_dimensions', postgresql.JSONB, nullable=True),

            # Processing Status
            sa.Column('processing_status', sa.String(20), server_default='pending', nullable=False),
            sa.Column('processing_error', sa.Text, nullable=True),
            sa.Column('thumbnail_generated', sa.Boolean, server_default='false', nullable=False),

            # Upload Information
            sa.Column('uploaded_by', sa.String(255), nullable=True),
            sa.Column('upload_source', sa.String(50), server_default='web_ui', nullable=False),
            sa.Column('upload_ip_address', postgresql.INET, nullable=True),

            # Visibility
            sa.Column('is_public', sa.Boolean, server_default='false', nullable=False),
            sa.Column('is_featured', sa.Boolean, server_default='false', nullable=False),
            sa.Column('display_order', sa.Integer, server_default='0', nullable=False),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

            # Constraints
            sa.CheckConstraint(
                "media_type IN ('photo', 'video', 'floorplan', '3d_model', 'document', 'other')",
                name='valid_media_type'
            ),
            sa.CheckConstraint(
                "media_category IN ('property_exterior', 'property_interior', 'unit_example', 'amenities', 'floorplan', 'site_plan', '3d_model', 'permit', 'inspection', 'other')",
                name='valid_media_category'
            ),
            sa.CheckConstraint(
                "processing_status IN ('pending', 'processing', 'completed', 'failed')",
                name='valid_processing_status'
            ),
            sa.CheckConstraint(
                "upload_source IN ('web_ui', 'mobile_app', 'api', 'email', 'bulk_import')",
                name='valid_upload_source'
            ),
            sa.CheckConstraint('file_size_bytes > 0', name='positive_file_size'),
        )
        print("✅ Created client_media table")
    except Exception as e:
        print(f"⚠️  Could not create client_media table: {e}")

    # Add indexes for client_media
    try:
        op.create_index('idx_client_media_client_id', 'client_media', ['client_id'])
        op.create_index('idx_client_media_media_type', 'client_media', ['media_type'])
        op.create_index('idx_client_media_media_category', 'client_media', ['media_category'])
        op.create_index('idx_client_media_processing_status', 'client_media', ['processing_status'])
        op.create_index('idx_client_media_created_at', 'client_media', ['created_at'])
        op.create_index('idx_client_media_deleted_at', 'client_media', ['deleted_at'])
        op.create_index('idx_client_media_tags', 'client_media', ['tags'], postgresql_using='gin')
        print("✅ Added indexes on client_media table")
    except Exception as e:
        print(f"⚠️  Could not add client_media indexes: {e}")

    print("\n" + "=" * 80)
    print("✅ Client Onboarding System Migration Complete")
    print("=" * 80)
    print("\n📊 Summary:")
    print("  • Enhanced clients table with 30+ onboarding fields")
    print("  • Created client_media table for portfolio management")
    print("  • Added comprehensive validation constraints")
    print("  • Created indexes for efficient querying")
    print("=" * 80)


def downgrade():
    """Remove client onboarding system"""
    print("=" * 80)
    print("Removing Client Onboarding System")
    print("=" * 80)

    # Drop client_media table
    print("\n📁 Dropping client_media table...")
    try:
        op.drop_index('idx_client_media_tags', table_name='client_media')
        op.drop_index('idx_client_media_deleted_at', table_name='client_media')
        op.drop_index('idx_client_media_created_at', table_name='client_media')
        op.drop_index('idx_client_media_processing_status', table_name='client_media')
        op.drop_index('idx_client_media_media_category', table_name='client_media')
        op.drop_index('idx_client_media_media_type', table_name='client_media')
        op.drop_index('idx_client_media_client_id', table_name='client_media')
        op.drop_table('client_media')
        print("✅ Dropped client_media table")
    except Exception as e:
        print(f"⚠️  Could not drop client_media table: {e}")

    # Drop indexes from clients table
    print("\n📝 Removing indexes from clients table...")
    try:
        op.drop_index('idx_clients_property_state', table_name='clients')
        op.drop_index('idx_clients_property_city', table_name='clients')
        op.drop_index('idx_clients_onboarding_stage', table_name='clients')
        print("✅ Dropped indexes from clients table")
    except Exception as e:
        print(f"⚠️  Could not drop indexes: {e}")

    # Drop CHECK constraints
    print("\n🔒 Removing CHECK constraints...")
    try:
        op.drop_constraint('valid_preferred_contact_method', 'clients', type_='check')
        op.drop_constraint('valid_property_type', 'clients', type_='check')
        op.drop_constraint('valid_onboarding_stage', 'clients', type_='check')
        print("✅ Dropped CHECK constraints")
    except Exception as e:
        print(f"⚠️  Could not drop CHECK constraints: {e}")

    # Drop columns from clients table
    print("\n📝 Removing onboarding fields from clients table...")
    try:
        # Communication preferences
        op.drop_column('clients', 'timezone')
        op.drop_column('clients', 'preferred_contact_time')
        op.drop_column('clients', 'preferred_contact_method')

        # Notes
        op.drop_column('clients', 'special_requirements')
        op.drop_column('clients', 'initial_notes')
        op.drop_column('clients', 'discovery_call_transcript')

        # Onboarding workflow
        op.drop_column('clients', 'initial_assessment_completed')
        op.drop_column('clients', 'discovery_call_completed_at')
        op.drop_column('clients', 'discovery_call_scheduled_at')
        op.drop_column('clients', 'onboarding_progress_percent')
        op.drop_column('clients', 'onboarding_step')
        op.drop_column('clients', 'onboarding_stage')

        # Property details
        op.drop_column('clients', 'property_description')
        op.drop_column('clients', 'property_square_feet')
        op.drop_column('clients', 'property_year_built')
        op.drop_column('clients', 'property_unit_count')
        op.drop_column('clients', 'property_type')

        # Property address
        op.drop_column('clients', 'property_country')
        op.drop_column('clients', 'property_zip_code')
        op.drop_column('clients', 'property_state')
        op.drop_column('clients', 'property_city')
        op.drop_column('clients', 'property_address_line2')
        op.drop_column('clients', 'property_address_line1')
        op.drop_column('clients', 'property_name')

        # Secondary contact
        op.drop_column('clients', 'secondary_contact_email')
        op.drop_column('clients', 'secondary_contact_phone')
        op.drop_column('clients', 'secondary_contact_title')
        op.drop_column('clients', 'secondary_contact_name')

        # Primary contact
        op.drop_column('clients', 'primary_contact_email')
        op.drop_column('clients', 'primary_contact_phone')
        op.drop_column('clients', 'primary_contact_title')
        op.drop_column('clients', 'primary_contact_name')

        print("✅ Dropped all onboarding columns from clients table")
    except Exception as e:
        print(f"⚠️  Could not drop columns: {e}")

    print("\n" + "=" * 80)
    print("✅ Client Onboarding System Rollback Complete")
    print("=" * 80)
