-- Migration: Add subscription tier fields to quotes table
-- Date: 2025-11-22

-- Add subscription tier tracking fields
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_service_hours_tier VARCHAR(50);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_service_hours_price NUMERIC(10, 2);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_smart_actions_tier VARCHAR(50);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_smart_actions_price NUMERIC(10, 2);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_analytics_tier VARCHAR(50);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS subscription_analytics_price NUMERIC(10, 2);

-- Add total calculation fields
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS monthly_subscription_total NUMERIC(10, 2);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS one_time_hardware_total NUMERIC(10, 2);
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS one_time_installation_total NUMERIC(10, 2);

-- Add billing period tracking
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS billing_period VARCHAR(20) DEFAULT 'monthly';

-- Add installation labor tracking
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS installation_hours NUMERIC(5, 2) DEFAULT 2.0;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS installation_rate NUMERIC(10, 2) DEFAULT 150.00;

-- Comments for documentation
COMMENT ON COLUMN quotes.subscription_service_hours_tier IS 'Service Hours tier: Pay Per Hour, Starter, Professional, Enterprise';
COMMENT ON COLUMN quotes.subscription_smart_actions_tier IS 'Smart Actions tier: Basic, Standard, Premium, Enterprise';
COMMENT ON COLUMN quotes.subscription_analytics_tier IS 'Analytics tier: Essential, Professional, Advanced, Enterprise';
COMMENT ON COLUMN quotes.monthly_subscription_total IS 'Total monthly recurring subscription fees';
COMMENT ON COLUMN quotes.one_time_hardware_total IS 'Total one-time hardware costs';
COMMENT ON COLUMN quotes.one_time_installation_total IS 'Total installation labor costs';
COMMENT ON COLUMN quotes.billing_period IS 'Billing period: monthly or annual';
COMMENT ON COLUMN quotes.installation_hours IS 'Total installation labor hours (2 hours included free)';

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_quotes_service_hours_tier ON quotes(subscription_service_hours_tier);
CREATE INDEX IF NOT EXISTS idx_quotes_billing_period ON quotes(billing_period);

-- Update existing quotes with default values
UPDATE quotes SET
    monthly_subscription_total = 0,
    one_time_hardware_total = 0,
    one_time_installation_total = 0,
    billing_period = 'monthly',
    installation_hours = 2.0,
    installation_rate = 150.00
WHERE monthly_subscription_total IS NULL;
