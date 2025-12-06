-- Migration: Add Home Assistant connection fields to clients table
-- Purpose: Link SomniProperty clients to their Home Assistant instances for MSP management

-- Add HA connection fields to clients table
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS ha_enabled BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS ha_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS ha_token_synced_to_infisical BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS ha_last_health_check TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS ha_health_status VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS ha_network_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS ha_instance_notes TEXT;

-- Add comments
COMMENT ON COLUMN clients.ha_enabled IS 'Whether Home Assistant management is enabled for this client';
COMMENT ON COLUMN clients.ha_url IS 'Full URL to client''s Home Assistant instance (e.g., https://ha.client.com or http://192.168.1.100:8123)';
COMMENT ON COLUMN clients.ha_token_synced_to_infisical IS 'Whether the HA token has been synced to Infisical';
COMMENT ON COLUMN clients.ha_last_health_check IS 'Timestamp of last successful health check';
COMMENT ON COLUMN clients.ha_health_status IS 'Current health status: healthy | timeout | error | unknown';
COMMENT ON COLUMN clients.ha_network_type IS 'How we access their HA: tailscale | cloudflare_tunnel | vpn | public_ip | local_network';
COMMENT ON COLUMN clients.ha_instance_notes IS 'Admin notes about this client''s HA instance';

-- Create index for HA enabled clients
CREATE INDEX IF NOT EXISTS idx_clients_ha_enabled ON clients(ha_enabled) WHERE ha_enabled = TRUE;

-- Create index for health status
CREATE INDEX IF NOT EXISTS idx_clients_ha_health_status ON clients(ha_health_status);
