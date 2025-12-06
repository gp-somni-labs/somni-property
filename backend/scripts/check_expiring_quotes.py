#!/usr/bin/env python3
"""
Quote Expiration Check Script

Runs as a CronJob to send reminder emails for quotes expiring soon
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from db.models_quotes import Quote as QuoteModel
from services.quote_email_service import quote_email_service


async def check_expiring_quotes():
    """Check for quotes expiring in 3 days and send reminders"""

    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return

    # Create async engine
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Find quotes expiring in 3 days
        three_days_from_now = datetime.utcnow() + timedelta(days=3)
        four_days_from_now = datetime.utcnow() + timedelta(days=4)

        query = select(QuoteModel).where(
            QuoteModel.status == 'sent',
            QuoteModel.valid_until >= three_days_from_now,
            QuoteModel.valid_until < four_days_from_now,
            QuoteModel.customer_email.isnot(None)
        )

        result = await session.execute(query)
        expiring_quotes = result.scalars().all()

        print(f"Found {len(expiring_quotes)} quotes expiring in 3 days")

        # Send reminder emails
        if quote_email_service:
            for quote in expiring_quotes:
                try:
                    # Generate portal URL
                    base_url = os.getenv('PUBLIC_BASE_URL', 'https://property.home.lan')
                    portal_url = f"{base_url}/customer-quotes/{quote.id}?token={quote.customer_portal_token}"

                    # Convert to dict
                    quote_dict = {
                        'quote_number': quote.quote_number,
                        'customer_name': quote.customer_name,
                        'customer_email': quote.customer_email,
                        'total_units': quote.total_units,
                        'monthly_total': quote.monthly_total,
                        'annual_total': quote.annual_total,
                        'valid_until': quote.valid_until
                    }

                    # Send reminder
                    sent = await quote_email_service.send_quote_reminder(
                        quote=quote_dict,
                        customer_portal_url=portal_url,
                        days_until_expiry=3
                    )

                    if sent:
                        print(f"✓ Sent reminder for quote {quote.quote_number}")
                    else:
                        print(f"✗ Failed to send reminder for quote {quote.quote_number}")

                except Exception as e:
                    print(f"Error sending reminder for quote {quote.quote_number}: {e}")
        else:
            print("WARNING: SendGrid not configured, no emails sent")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_expiring_quotes())
