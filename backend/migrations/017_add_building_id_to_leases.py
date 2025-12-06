"""
Migration 017: Add building_id to leases table

Per spec §4.3, leases should have a direct building_id FK for easier filtering
and portfolio management.

This migration:
1. Adds building_id column to leases table
2. Populates it from units.building_id for existing leases
3. Adds index for building_id
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add building_id column to leases table"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    conn = await asyncpg.connect(database_url)

    try:
        print("Starting migration 017: Add building_id to leases...")

        # 1. Add building_id column (nullable initially)
        print("  - Adding building_id column to leases...")
        await conn.execute("""
            ALTER TABLE leases
            ADD COLUMN IF NOT EXISTS building_id UUID
            REFERENCES buildings(id) ON DELETE CASCADE;
        """)

        # 2. Populate building_id from units table for existing leases
        print("  - Populating building_id from units...")
        result = await conn.execute("""
            UPDATE leases
            SET building_id = units.building_id
            FROM units
            WHERE leases.unit_id = units.id
            AND leases.building_id IS NULL;
        """)
        print(f"    Updated {result.split()[-1]} lease records")

        # 3. Add index for building_id
        print("  - Creating index on building_id...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_leases_building_id
            ON leases(building_id);
        """)

        print("✓ Migration 017 completed successfully!")

    except Exception as e:
        print(f"✗ Migration 017 failed: {e}")
        raise
    finally:
        await conn.close()


async def rollback():
    """Rollback: Remove building_id column from leases"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    conn = await asyncpg.connect(database_url)

    try:
        print("Rolling back migration 017...")

        # Drop index
        await conn.execute("""
            DROP INDEX IF EXISTS idx_leases_building_id;
        """)

        # Drop column
        await conn.execute("""
            ALTER TABLE leases
            DROP COLUMN IF EXISTS building_id;
        """)

        print("✓ Rollback completed")

    except Exception as e:
        print(f"✗ Rollback failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
