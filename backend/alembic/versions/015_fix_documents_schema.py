"""Fix documents table schema to match model

Revision ID: 015_fix_documents_schema
Revises: caa2a763b596
Create Date: 2025-11-20

Changes:
- Rename 'notes' column to 'description'
- Add 'file_url' column
- Add 'upload_date' column
- Add 'uploaded_by' column
- Add 'docuseal_metadata' JSONB column
- Update signing_status values to match model
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '015_fix_documents_schema'
down_revision = 'caa2a763b596'
branch_labels = None
depends_on = None


def upgrade():
    """Fix documents table schema"""
    print("=" * 80)
    print("Fixing Documents Table Schema")
    print("=" * 80)

    # Rename notes to description
    try:
        op.alter_column('documents', 'notes', new_column_name='description')
        print("✅ Renamed 'notes' column to 'description'")
    except Exception as e:
        print(f"⚠️ Could not rename notes column: {e}")

    # Add missing columns
    try:
        op.add_column('documents', sa.Column('file_url', sa.Text, nullable=True))
        print("✅ Added 'file_url' column")
    except Exception as e:
        print(f"⚠️ Could not add file_url: {e}")

    try:
        op.add_column('documents', sa.Column('upload_date', sa.Date, server_default=sa.text('CURRENT_DATE'), nullable=True))
        print("✅ Added 'upload_date' column")
    except Exception as e:
        print(f"⚠️ Could not add upload_date: {e}")

    try:
        op.add_column('documents', sa.Column('uploaded_by', sa.String(255), nullable=True))
        print("✅ Added 'uploaded_by' column")
    except Exception as e:
        print(f"⚠️ Could not add uploaded_by: {e}")

    try:
        op.add_column('documents', sa.Column('docuseal_metadata', JSONB, nullable=True))
        print("✅ Added 'docuseal_metadata' column")
    except Exception as e:
        print(f"⚠️ Could not add docuseal_metadata: {e}")

    # Update signing_status CHECK constraint to match new model
    try:
        op.drop_constraint('valid_signing_status', 'documents', type_='check')
        op.create_check_constraint(
            'valid_signing_status',
            'documents',
            "signing_status IN ('draft', 'pending', 'partially_signed', 'signed', 'cancelled', 'expired')"
        )
        print("✅ Updated signing_status constraint")
    except Exception as e:
        print(f"⚠️ Could not update signing_status constraint: {e}")

    # Update default value for signing_status
    try:
        op.alter_column('documents', 'signing_status', server_default='draft')
        print("✅ Updated signing_status default to 'draft'")
    except Exception as e:
        print(f"⚠️ Could not update signing_status default: {e}")

    print("\n" + "=" * 80)
    print("✅ Documents Schema Migration Complete")
    print("=" * 80)


def downgrade():
    """Revert documents table schema changes"""
    print("=" * 80)
    print("Reverting Documents Schema Changes")
    print("=" * 80)

    # Revert signing_status default and constraint
    op.alter_column('documents', 'signing_status', server_default='unsigned')
    op.drop_constraint('valid_signing_status', 'documents', type_='check')
    op.create_check_constraint(
        'valid_signing_status',
        'documents',
        "signing_status IN ('unsigned', 'pending', 'signed', 'expired', 'declined')"
    )
    print("✅ Reverted signing_status constraint")

    # Drop added columns
    op.drop_column('documents', 'docuseal_metadata')
    op.drop_column('documents', 'uploaded_by')
    op.drop_column('documents', 'upload_date')
    op.drop_column('documents', 'file_url')
    print("✅ Dropped added columns")

    # Rename description back to notes
    op.alter_column('documents', 'description', new_column_name='notes')
    print("✅ Renamed 'description' back to 'notes'")

    print("\n" + "=" * 80)
    print("✅ Documents Schema Rollback Complete")
    print("=" * 80)
