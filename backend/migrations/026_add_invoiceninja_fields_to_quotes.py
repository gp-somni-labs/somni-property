"""
Migration: Add Invoice Ninja integration fields to quotes table
Adds fields for tracking Invoice Ninja client/invoice IDs and customer acceptance

Run this migration to add support for:
- Invoice Ninja client tracking
- Invoice creation from accepted quotes
- Customer signature capture
- Service address storage
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from db.database import async_engine
from sqlalchemy import text


async def add_invoiceninja_fields():
    """Add Invoice Ninja integration fields to quotes table"""

    alter_sql = """
    -- Invoice Ninja integration fields
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS invoice_ninja_client_id VARCHAR(255);
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS invoice_ninja_invoice_id VARCHAR(255);
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS invoice_ninja_invoice_number VARCHAR(100);

    -- Customer acceptance fields
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS customer_signature TEXT;
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS acceptance_notes TEXT;

    -- Service location (for quotes not linked to a specific property)
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS service_address TEXT;

    -- Total amount convenience field
    ALTER TABLE quotes ADD COLUMN IF NOT EXISTS total_amount NUMERIC(12, 2);

    -- Add indexes for Invoice Ninja lookups
    CREATE INDEX IF NOT EXISTS idx_quotes_invoice_ninja_client_id ON quotes(invoice_ninja_client_id);
    CREATE INDEX IF NOT EXISTS idx_quotes_invoice_ninja_invoice_id ON quotes(invoice_ninja_invoice_id);
    """

    async with async_engine.begin() as conn:
        print("Adding Invoice Ninja integration fields to quotes table...")
        await conn.execute(text(alter_sql))
        print("Migration completed successfully!")


async def rollback():
    """Rollback migration - remove added columns"""

    rollback_sql = """
    -- Remove indexes
    DROP INDEX IF EXISTS idx_quotes_invoice_ninja_client_id;
    DROP INDEX IF EXISTS idx_quotes_invoice_ninja_invoice_id;

    -- Remove columns
    ALTER TABLE quotes DROP COLUMN IF EXISTS invoice_ninja_client_id;
    ALTER TABLE quotes DROP COLUMN IF EXISTS invoice_ninja_invoice_id;
    ALTER TABLE quotes DROP COLUMN IF EXISTS invoice_ninja_invoice_number;
    ALTER TABLE quotes DROP COLUMN IF EXISTS customer_signature;
    ALTER TABLE quotes DROP COLUMN IF EXISTS acceptance_notes;
    ALTER TABLE quotes DROP COLUMN IF EXISTS service_address;
    ALTER TABLE quotes DROP COLUMN IF EXISTS total_amount;
    """

    async with async_engine.begin() as conn:
        print("Rolling back Invoice Ninja fields from quotes table...")
        await conn.execute(text(rollback_sql))
        print("Rollback completed successfully!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Invoice Ninja integration migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback())
    else:
        asyncio.run(add_invoiceninja_fields())
