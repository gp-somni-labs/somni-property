"""
Migration 018: Add quote fields to support_tickets table

Per spec §3.4 and §5.8, support requests need quote/estimate fields.

This migration adds:
1. quote_requested boolean
2. quote_amount numeric
3. quote_notes text
4. quote_provided_at timestamp
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add quote fields to support_tickets table"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    conn = await asyncpg.connect(database_url)

    try:
        print("Starting migration 018: Add quote fields to support_tickets...")

        # 1. Add quote_requested column
        print("  - Adding quote_requested column...")
        await conn.execute("""
            ALTER TABLE support_tickets
            ADD COLUMN IF NOT EXISTS quote_requested BOOLEAN DEFAULT FALSE;
        """)

        # 2. Add quote_amount column
        print("  - Adding quote_amount column...")
        await conn.execute("""
            ALTER TABLE support_tickets
            ADD COLUMN IF NOT EXISTS quote_amount NUMERIC(10, 2);
        """)

        # 3. Add quote_notes column
        print("  - Adding quote_notes column...")
        await conn.execute("""
            ALTER TABLE support_tickets
            ADD COLUMN IF NOT EXISTS quote_notes TEXT;
        """)

        # 4. Add quote_provided_at timestamp
        print("  - Adding quote_provided_at column...")
        await conn.execute("""
            ALTER TABLE support_tickets
            ADD COLUMN IF NOT EXISTS quote_provided_at TIMESTAMP WITH TIME ZONE;
        """)

        # 5. Add index for quote_requested
        print("  - Creating index on quote_requested...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_support_tickets_quote_requested
            ON support_tickets(quote_requested);
        """)

        print("✓ Migration 018 completed successfully!")

    except Exception as e:
        print(f"✗ Migration 018 failed: {e}")
        raise
    finally:
        await conn.close()


async def rollback():
    """Rollback: Remove quote fields from support_tickets"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    conn = await asyncpg.connect(database_url)

    try:
        print("Rolling back migration 018...")

        # Drop index
        await conn.execute("""
            DROP INDEX IF EXISTS idx_support_tickets_quote_requested;
        """)

        # Drop columns
        await conn.execute("""
            ALTER TABLE support_tickets
            DROP COLUMN IF EXISTS quote_requested,
            DROP COLUMN IF EXISTS quote_amount,
            DROP COLUMN IF EXISTS quote_notes,
            DROP COLUMN IF EXISTS quote_provided_at;
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
