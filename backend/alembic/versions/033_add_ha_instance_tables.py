"""Add Home Assistant instance management tables for unified Flutter app

Creates tables for:
- ha_instances: HA instance configuration and status tracking
- ha_terminal_sessions: SSH terminal session audit logs
- ha_log_analyses: Claude-powered log analysis requests and results
- ha_command_approvals: Command approval workflow for AI-suggested fixes

Revision ID: 033
Revises: 032
Create Date: 2025-12-03 08:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision = '033'
down_revision = '032'


def upgrade() -> None:
    """Create HA instance management tables"""

    # ==========================================================================
    # HA INSTANCES TABLE
    # ==========================================================================
    op.create_table(
        'ha_instances',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Basic Info
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer, default=8123),
        sa.Column('location', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('tags', JSONB, server_default='[]'),

        # SSH Configuration
        sa.Column('ssh_port', sa.Integer, default=22),
        sa.Column('ssh_user', sa.String(100), default='root'),
        sa.Column('ssh_key_name', sa.String(255)),

        # Home Assistant API
        sa.Column('ha_api_url', sa.String(500)),
        sa.Column('ha_api_token_encrypted', sa.Text),

        # Status Tracking
        sa.Column('status', sa.String(50), default='unknown'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True)),
        sa.Column('last_status_check_at', sa.DateTime(timezone=True)),
        sa.Column('status_message', sa.String(500)),

        # Home Assistant Info
        sa.Column('ha_version', sa.String(50)),
        sa.Column('supervisor_version', sa.String(50)),
        sa.Column('os_type', sa.String(50)),
        sa.Column('uptime_seconds', sa.Integer),

        # Somni Component Tracking
        sa.Column('installed_somni_components', JSONB, server_default='{}'),
        sa.Column('last_component_sync_at', sa.DateTime(timezone=True)),
        sa.Column('last_component_sync_id', UUID(as_uuid=True),
                  sa.ForeignKey('component_syncs.id', ondelete='SET NULL')),

        # Optional Property Link
        sa.Column('property_edge_node_id', UUID(as_uuid=True),
                  sa.ForeignKey('property_edge_nodes.id', ondelete='SET NULL')),

        # Instance Type and Enabled flag
        sa.Column('instance_type', sa.String(50), default='family'),
        sa.Column('is_enabled', sa.Boolean, default=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(255)),

        # Constraints
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'error', 'maintenance', 'unknown')",
            name='valid_ha_instance_status'
        ),
        sa.CheckConstraint(
            "instance_type IN ('family', 'property', 'development', 'test')",
            name='valid_ha_instance_type'
        ),
        sa.CheckConstraint(
            "os_type IN ('ha_os', 'container', 'core', 'supervised') OR os_type IS NULL",
            name='valid_ha_os_type'
        ),
    )

    # Indexes for ha_instances
    op.create_index('idx_ha_instances_host', 'ha_instances', ['host'])
    op.create_index('idx_ha_instances_status', 'ha_instances', ['status'])
    op.create_index('idx_ha_instances_instance_type', 'ha_instances', ['instance_type'])
    op.create_index('idx_ha_instances_is_enabled', 'ha_instances', ['is_enabled'])
    op.create_index('idx_ha_instances_last_seen_at', 'ha_instances', ['last_seen_at'])
    op.create_index('idx_ha_instances_property_edge_node_id', 'ha_instances', ['property_edge_node_id'])
    op.create_index('idx_ha_instances_tags', 'ha_instances', ['tags'], postgresql_using='gin')

    # ==========================================================================
    # HA TERMINAL SESSIONS TABLE
    # ==========================================================================
    op.create_table(
        'ha_terminal_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('instance_id', UUID(as_uuid=True),
                  sa.ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False),

        # Session Info
        sa.Column('session_status', sa.String(30), default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True)),

        # User Info
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('user_ip', INET),

        # Session Stats
        sa.Column('commands_executed', sa.Integer, default=0),
        sa.Column('bytes_transferred', sa.Integer, default=0),

        # Error Tracking
        sa.Column('disconnect_reason', sa.String(500)),

        # Constraints
        sa.CheckConstraint(
            "session_status IN ('active', 'disconnected', 'error')",
            name='valid_terminal_session_status'
        ),
    )

    # Indexes for ha_terminal_sessions
    op.create_index('idx_terminal_sessions_instance_id', 'ha_terminal_sessions', ['instance_id'])
    op.create_index('idx_terminal_sessions_user_id', 'ha_terminal_sessions', ['user_id'])
    op.create_index('idx_terminal_sessions_status', 'ha_terminal_sessions', ['session_status'])
    op.create_index('idx_terminal_sessions_started_at', 'ha_terminal_sessions', ['started_at'])

    # ==========================================================================
    # HA LOG ANALYSES TABLE
    # ==========================================================================
    op.create_table(
        'ha_log_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('instance_id', UUID(as_uuid=True),
                  sa.ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False),

        # Analysis Request
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('additional_instance_ids', JSONB, server_default='[]'),
        sa.Column('log_types', JSONB, server_default='[]'),
        sa.Column('time_range_hours', sa.Integer, default=24),

        # Analysis Status
        sa.Column('analysis_status', sa.String(30), default='pending'),

        # Analysis Results
        sa.Column('analysis_text', sa.Text),
        sa.Column('suggested_commands', JSONB, server_default='[]'),
        sa.Column('logs_reviewed_count', sa.Integer),

        # Timing
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('duration_seconds', sa.Integer),

        # User Info
        sa.Column('submitted_by', sa.String(255), nullable=False),

        # Error Tracking
        sa.Column('error_message', sa.Text),

        # Constraints
        sa.CheckConstraint(
            "analysis_status IN ('pending', 'analyzing', 'completed', 'failed')",
            name='valid_log_analysis_status'
        ),
    )

    # Indexes for ha_log_analyses
    op.create_index('idx_log_analyses_instance_id', 'ha_log_analyses', ['instance_id'])
    op.create_index('idx_log_analyses_status', 'ha_log_analyses', ['analysis_status'])
    op.create_index('idx_log_analyses_submitted_by', 'ha_log_analyses', ['submitted_by'])
    op.create_index('idx_log_analyses_submitted_at', 'ha_log_analyses', ['submitted_at'])

    # ==========================================================================
    # HA COMMAND APPROVALS TABLE
    # ==========================================================================
    op.create_table(
        'ha_command_approvals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', UUID(as_uuid=True),
                  sa.ForeignKey('ha_log_analyses.id', ondelete='CASCADE'), nullable=False),

        # Command Info
        sa.Column('target_instance_id', UUID(as_uuid=True),
                  sa.ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('command', sa.Text, nullable=False),
        sa.Column('reason', sa.Text),

        # Approval Status
        sa.Column('approval_status', sa.String(30), default='pending'),

        # Approval Decision
        sa.Column('approved_by', sa.String(255)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('rejection_reason', sa.Text),

        # Execution Results
        sa.Column('executed_at', sa.DateTime(timezone=True)),
        sa.Column('execution_output', sa.Text),
        sa.Column('exit_code', sa.Integer),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'executed', 'failed')",
            name='valid_command_approval_status'
        ),
    )

    # Indexes for ha_command_approvals
    op.create_index('idx_command_approvals_analysis_id', 'ha_command_approvals', ['analysis_id'])
    op.create_index('idx_command_approvals_target_instance_id', 'ha_command_approvals', ['target_instance_id'])
    op.create_index('idx_command_approvals_status', 'ha_command_approvals', ['approval_status'])
    op.create_index('idx_command_approvals_created_at', 'ha_command_approvals', ['created_at'])


def downgrade() -> None:
    """Drop HA instance management tables"""
    # Drop indexes first (handled automatically with table drop)
    # Drop tables in reverse order of dependencies
    op.drop_table('ha_command_approvals')
    op.drop_table('ha_log_analyses')
    op.drop_table('ha_terminal_sessions')
    op.drop_table('ha_instances')
