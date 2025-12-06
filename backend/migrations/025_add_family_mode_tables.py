"""
Direct SQL migration to create Family Mode tables
Run this when Alembic migration chain is broken
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from db.database import async_engine
from sqlalchemy import text

async def create_family_tables():
    """Create all Family Mode tables"""

    # SQL statements to create tables
    create_enums_sql = """
    DO $$ BEGIN
        CREATE TYPE subscriptiontier AS ENUM ('starter', 'pro', 'enterprise');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    DO $$ BEGIN
        CREATE TYPE subscriptionstatus AS ENUM ('active', 'cancelled', 'past_due', 'suspended');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    DO $$ BEGIN
        CREATE TYPE ticketpriority AS ENUM ('low', 'medium', 'high', 'critical');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    DO $$ BEGIN
        CREATE TYPE ticketstatus AS ENUM ('open', 'in_progress', 'waiting_customer', 'resolved', 'closed');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    DO $$ BEGIN
        CREATE TYPE alertseverity AS ENUM ('info', 'warning', 'critical');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    DO $$ BEGIN
        CREATE TYPE alertstatus AS ENUM ('active', 'acknowledged', 'resolved', 'dismissed');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """

    create_family_subscriptions_sql = """
    CREATE TABLE IF NOT EXISTS family_subscriptions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        client_id UUID NOT NULL REFERENCES clients(id),
        tier subscriptiontier NOT NULL DEFAULT 'starter',
        status subscriptionstatus NOT NULL DEFAULT 'active',
        base_price FLOAT NOT NULL,
        included_support_hours INTEGER NOT NULL,
        overage_rate FLOAT NOT NULL,
        billing_cycle_start TIMESTAMP NOT NULL,
        next_billing_date TIMESTAMP NOT NULL,
        auto_renew BOOLEAN DEFAULT true,
        addons JSONB DEFAULT '{}',
        started_at TIMESTAMP NOT NULL,
        cancelled_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS ix_family_subscriptions_client_id ON family_subscriptions(client_id);
    CREATE INDEX IF NOT EXISTS ix_family_subscriptions_status ON family_subscriptions(status);
    """

    create_family_billing_sql = """
    CREATE TABLE IF NOT EXISTS family_billing (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subscription_id UUID NOT NULL REFERENCES family_subscriptions(id),
        billing_period_start TIMESTAMP NOT NULL,
        billing_period_end TIMESTAMP NOT NULL,
        invoice_date TIMESTAMP NOT NULL DEFAULT NOW(),
        billing_date TIMESTAMP NOT NULL DEFAULT NOW(),
        due_date TIMESTAMP NOT NULL,
        base_subscription FLOAT NOT NULL,
        addons_total FLOAT DEFAULT 0.0,
        support_hours_base FLOAT DEFAULT 0.0,
        support_hours_overage FLOAT DEFAULT 0.0,
        custom_services FLOAT DEFAULT 0.0,
        hardware_charges FLOAT DEFAULT 0.0,
        subtotal FLOAT NOT NULL,
        tax FLOAT DEFAULT 0.0,
        total FLOAT NOT NULL,
        amount_due FLOAT NOT NULL,
        paid BOOLEAN DEFAULT false,
        paid_at TIMESTAMP,
        payment_method VARCHAR(100),
        transaction_id VARCHAR(255),
        line_items JSONB DEFAULT '[]',
        status VARCHAR(50) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS ix_family_billing_subscription_id ON family_billing(subscription_id);
    CREATE INDEX IF NOT EXISTS ix_family_billing_paid ON family_billing(paid);
    """

    create_support_hours_sql = """
    CREATE TABLE IF NOT EXISTS support_hours (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subscription_id UUID NOT NULL REFERENCES family_subscriptions(id),
        billing_cycle_start TIMESTAMP NOT NULL,
        billing_cycle_end TIMESTAMP NOT NULL,
        included_hours INTEGER NOT NULL,
        used_hours FLOAT DEFAULT 0.0,
        overage_hours FLOAT DEFAULT 0.0,
        base_cost FLOAT DEFAULT 0.0,
        overage_cost FLOAT DEFAULT 0.0,
        total_cost FLOAT DEFAULT 0.0,
        support_sessions JSONB DEFAULT '[]',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS ix_support_hours_subscription_id ON support_hours(subscription_id);
    """

    create_family_support_tickets_sql = """
    CREATE TABLE IF NOT EXISTS family_support_tickets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subscription_id UUID NOT NULL REFERENCES family_subscriptions(id),
        ticket_number VARCHAR(50) UNIQUE NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        priority ticketpriority NOT NULL DEFAULT 'medium',
        status ticketstatus NOT NULL DEFAULT 'open',
        category VARCHAR(100),
        assigned_to VARCHAR(255),
        assigned_at TIMESTAMP,
        first_response_at TIMESTAMP,
        resolved_at TIMESTAMP,
        closed_at TIMESTAMP,
        sla_response_time_hours INTEGER,
        sla_resolution_time_hours INTEGER,
        sla_response_breached BOOLEAN DEFAULT false,
        sla_resolution_breached BOOLEAN DEFAULT false,
        customer_name VARCHAR(255),
        customer_email VARCHAR(255),
        customer_phone VARCHAR(50),
        device_id UUID REFERENCES smart_devices(id),
        hub_id UUID REFERENCES property_edge_nodes(id),
        error_logs TEXT,
        tags JSONB DEFAULT '[]',
        attachments JSONB DEFAULT '[]',
        internal_notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS ix_family_support_tickets_subscription_id ON family_support_tickets(subscription_id);
    CREATE INDEX IF NOT EXISTS ix_family_support_tickets_status ON family_support_tickets(status);
    """

    create_remaining_tables_sql = """
    CREATE TABLE IF NOT EXISTS support_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subscription_id UUID NOT NULL REFERENCES family_subscriptions(id),
        ticket_id UUID REFERENCES support_tickets(id),
        title VARCHAR(255) NOT NULL,
        description TEXT,
        support_engineer VARCHAR(255),
        duration_minutes INTEGER NOT NULL,
        duration_hours FLOAT NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        billable BOOLEAN DEFAULT true,
        hourly_rate FLOAT,
        total_cost FLOAT,
        notes TEXT,
        work_performed TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ticket_comments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticket_id UUID NOT NULL REFERENCES family_support_tickets(id),
        author_name VARCHAR(255) NOT NULL,
        author_email VARCHAR(255) NOT NULL,
        author_type VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        is_internal BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS family_alerts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        subscription_id UUID NOT NULL REFERENCES family_subscriptions(id),
        title VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        severity alertseverity NOT NULL DEFAULT 'info',
        status alertstatus NOT NULL DEFAULT 'active',
        source_type VARCHAR(100),
        source_id VARCHAR(255),
        source_name VARCHAR(255),
        device_id UUID REFERENCES smart_devices(id),
        hub_id UUID REFERENCES property_edge_nodes(id),
        acknowledged_at TIMESTAMP,
        acknowledged_by VARCHAR(255),
        resolved_at TIMESTAMP,
        resolved_by VARCHAR(255),
        resolution_notes TEXT,
        escalated BOOLEAN DEFAULT false,
        escalated_to_ticket UUID REFERENCES family_support_tickets(id),
        escalated_at TIMESTAMP,
        notifications_sent JSONB DEFAULT '[]',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS automation_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        category VARCHAR(100),
        required_devices JSONB DEFAULT '[]',
        tier_requirement subscriptiontier DEFAULT 'starter',
        is_premium BOOLEAN DEFAULT false,
        setup_fee FLOAT DEFAULT 0.0,
        monthly_fee FLOAT DEFAULT 0.0,
        ha_automation_yaml TEXT,
        configuration_schema JSONB,
        icon VARCHAR(100),
        thumbnail_url VARCHAR(500),
        popularity_score INTEGER DEFAULT 0,
        active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """

    async with async_engine.begin() as conn:
        try:
            print("Creating enum types...")
            await conn.execute(text(create_enums_sql))
            print("✅ Enum types created")

            print("Creating family_subscriptions table...")
            await conn.execute(text(create_family_subscriptions_sql))
            print("✅ family_subscriptions table created")

            print("Creating family_billing table...")
            await conn.execute(text(create_family_billing_sql))
            print("✅ family_billing table created")

            print("Creating support_hours table...")
            await conn.execute(text(create_support_hours_sql))
            print("✅ support_hours table created")

            print("Creating family_support_tickets table...")
            await conn.execute(text(create_family_support_tickets_sql))
            print("✅ family_support_tickets table created")

            print("Creating remaining tables...")
            await conn.execute(text(create_remaining_tables_sql))
            print("✅ All remaining tables created")

            await conn.commit()
            print("\n🎉 All Family Mode tables created successfully!")

        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_family_tables())
