"""
Migration 015: Create Audit Logs Table
EPIC K: RBAC Role Matrix + Route Guards

Creates audit_logs table for comprehensive audit trail of all critical actions
"""

from yoyo import step

__depends__ = {'014_create_support_tickets'}

steps = [
    step(
        # Create audit_logs table
        """
        CREATE TABLE audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- User information
            user_id VARCHAR(255) NOT NULL,
            user_email VARCHAR(255),
            user_role VARCHAR(20),

            -- Action details
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id UUID,

            -- Change tracking (for updates)
            changes JSONB,

            -- Request details
            http_method VARCHAR(10),
            endpoint VARCHAR(500),
            ip_address INET,
            user_agent VARCHAR(500),

            -- Status
            status_code INTEGER,
            success BOOLEAN DEFAULT true,
            error_message TEXT,

            -- Timing
            timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            duration_ms INTEGER
        );
        """,
        # Rollback
        "DROP TABLE IF EXISTS audit_logs;"
    ),

    step(
        # Create indexes for efficient querying
        """
        CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
        CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
        CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
        CREATE INDEX idx_audit_logs_action ON audit_logs(action);
        CREATE INDEX idx_audit_logs_user_role ON audit_logs(user_role);
        CREATE INDEX idx_audit_logs_success ON audit_logs(success);
        """,
        # Rollback
        """
        DROP INDEX IF EXISTS idx_audit_logs_user_id;
        DROP INDEX IF EXISTS idx_audit_logs_timestamp;
        DROP INDEX IF EXISTS idx_audit_logs_resource;
        DROP INDEX IF EXISTS idx_audit_logs_action;
        DROP INDEX IF EXISTS idx_audit_logs_user_role;
        DROP INDEX IF EXISTS idx_audit_logs_success;
        """
    ),

    step(
        # Add comment to table
        """
        COMMENT ON TABLE audit_logs IS 'EPIC K: Comprehensive audit trail for RBAC system. Tracks all critical actions including deployments, access control changes, lease edits, payments, etc.';
        """,
        ""
    ),

    step(
        # Add comments to important columns
        """
        COMMENT ON COLUMN audit_logs.user_id IS 'Username from Authelia (X-Forwarded-User header)';
        COMMENT ON COLUMN audit_logs.user_role IS 'Role at time of action: admin, operator, technician, read_only';
        COMMENT ON COLUMN audit_logs.action IS 'Action performed: created_deployment, updated_hub, deleted_lease, etc.';
        COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource: deployment, hub, work_order, lease, payment, etc.';
        COMMENT ON COLUMN audit_logs.changes IS 'JSON object with old/new values for updates: {"old": {...}, "new": {...}}';
        COMMENT ON COLUMN audit_logs.success IS 'True if action succeeded (status_code < 400), false otherwise';
        """,
        ""
    ),
]
