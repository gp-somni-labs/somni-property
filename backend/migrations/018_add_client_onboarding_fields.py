"""
Migration 018: Add Client Onboarding Fields
Adds comprehensive onboarding workflow fields to clients table
"""

import asyncio
from db.database import AsyncSessionLocal
from sqlalchemy import text

async def run_migration():
    async with AsyncSessionLocal() as session:
        print("🔄 Migration 018: Adding client onboarding fields...")

        # Add onboarding workflow fields
        await session.execute(text("""
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS onboarding_stage VARCHAR(50) DEFAULT 'initial' NOT NULL,
            ADD COLUMN IF NOT EXISTS onboarding_step INTEGER DEFAULT 1 NOT NULL,
            ADD COLUMN IF NOT EXISTS onboarding_progress_percent INTEGER DEFAULT 0 NOT NULL,
            ADD COLUMN IF NOT EXISTS discovery_call_scheduled_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS discovery_call_completed_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS initial_assessment_completed BOOLEAN DEFAULT FALSE NOT NULL;
        """))

        # Add contact information fields
        await session.execute(text("""
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS primary_contact_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS primary_contact_title VARCHAR(100),
            ADD COLUMN IF NOT EXISTS primary_contact_phone VARCHAR(20),
            ADD COLUMN IF NOT EXISTS primary_contact_email VARCHAR(255),
            ADD COLUMN IF NOT EXISTS secondary_contact_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS secondary_contact_title VARCHAR(100),
            ADD COLUMN IF NOT EXISTS secondary_contact_phone VARCHAR(20),
            ADD COLUMN IF NOT EXISTS secondary_contact_email VARCHAR(255);
        """))

        # Add property information fields
        await session.execute(text("""
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS property_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS property_address_line1 VARCHAR(255),
            ADD COLUMN IF NOT EXISTS property_address_line2 VARCHAR(255),
            ADD COLUMN IF NOT EXISTS property_city VARCHAR(100),
            ADD COLUMN IF NOT EXISTS property_state VARCHAR(50),
            ADD COLUMN IF NOT EXISTS property_zip_code VARCHAR(20),
            ADD COLUMN IF NOT EXISTS property_country VARCHAR(100) DEFAULT 'USA';
        """))

        # Add property details fields
        await session.execute(text("""
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS property_type VARCHAR(50),
            ADD COLUMN IF NOT EXISTS property_unit_count INTEGER,
            ADD COLUMN IF NOT EXISTS property_year_built INTEGER,
            ADD COLUMN IF NOT EXISTS property_square_feet INTEGER,
            ADD COLUMN IF NOT EXISTS property_description TEXT;
        """))

        # Add communication and workflow fields
        await session.execute(text("""
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS discovery_call_transcript TEXT,
            ADD COLUMN IF NOT EXISTS initial_notes TEXT,
            ADD COLUMN IF NOT EXISTS special_requirements TEXT,
            ADD COLUMN IF NOT EXISTS preferred_contact_method VARCHAR(20) DEFAULT 'email',
            ADD COLUMN IF NOT EXISTS preferred_contact_time VARCHAR(50),
            ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'America/New_York';
        """))

        await session.commit()
        print("✅ Migration 018 complete!")
        print("   - Added 30+ onboarding workflow fields to clients table")

if __name__ == "__main__":
    asyncio.run(run_migration())
