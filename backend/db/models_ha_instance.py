"""
Home Assistant Instance Models
Standalone HA instance tracking for the unified Flutter app.

These models support HA instances that are NOT linked to properties (e.g., family homes)
as well as property-linked instances via optional PropertyEdgeNode relationship.
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean,
    Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from db.types import GUID, INET, JSONB
from db.models import Base


# ============================================================================
# HOME ASSISTANT INSTANCE MANAGEMENT
# ============================================================================

class HAInstance(Base):
    """
    Home Assistant instance configuration for unified Flutter app.

    Supports both:
    1. Standalone HA instances (family homes not in property management)
    2. Property-linked instances (via optional property_edge_node_id)

    Used by the somni-ha-manager Flutter app for:
    - Dashboard: View all HA instances with status
    - Terminal: SSH access via WebSocket proxy
    - Component Sync: Deploy Somni custom components
    - Log Analysis: AI-powered log analysis with Claude
    """
    __tablename__ = "ha_instances"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Basic Info
    name = Column(String(255), nullable=False)  # Display name (e.g., "George's Home")
    host = Column(String(255), nullable=False)  # Tailscale IP (100.x.x.x)
    port = Column(Integer, default=8123)  # HA web UI port
    location = Column(String(255))  # Physical location description
    description = Column(Text)  # Additional notes
    tags = Column(JSONB, default=list)  # Searchable tags: ["family", "development", "production"]

    # SSH Configuration
    ssh_port = Column(Integer, default=22)
    ssh_user = Column(String(100), default="root")
    ssh_key_name = Column(String(255))  # Reference to SSH key in Kubernetes secret

    # Home Assistant API
    ha_api_url = Column(String(500))  # Full API URL (e.g., http://100.x.x.x:8123/api)
    ha_api_token_encrypted = Column(Text)  # Fernet-encrypted long-lived access token

    # Status Tracking
    status = Column(String(50), default='unknown')  # online, offline, error, maintenance
    last_seen_at = Column(DateTime(timezone=True))  # Last successful connection
    last_status_check_at = Column(DateTime(timezone=True))  # Last status check attempt
    status_message = Column(String(500))  # Human-readable status (e.g., "Connected, HA version 2024.12.1")

    # Home Assistant Info (from status check)
    ha_version = Column(String(50))  # Home Assistant version
    supervisor_version = Column(String(50))  # Supervisor version (if HA OS)
    os_type = Column(String(50))  # ha_os, container, core, supervised
    uptime_seconds = Column(Integer)  # HA uptime in seconds

    # Somni Component Tracking
    installed_somni_components = Column(JSONB, default=dict)  # {"somni_lights": true, "somni_occupancy": false}
    last_component_sync_at = Column(DateTime(timezone=True))
    last_component_sync_id = Column(GUID, ForeignKey('component_syncs.id', ondelete='SET NULL'))

    # Optional Property Link
    # If this HA instance is linked to a property, reference the PropertyEdgeNode
    property_edge_node_id = Column(GUID, ForeignKey('property_edge_nodes.id', ondelete='SET NULL'))

    # Instance Type
    instance_type = Column(String(50), default='family')  # family, property, development, test

    # Enabled/Disabled
    is_enabled = Column(Boolean, default=True)  # Can disable without deleting

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))  # Username who added this instance

    # Relationships
    property_edge_node = relationship("PropertyEdgeNode", foreign_keys=[property_edge_node_id])
    terminal_sessions = relationship("HATerminalSession", back_populates="instance", cascade="all, delete-orphan")
    log_analyses = relationship("HALogAnalysis", back_populates="instance", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('online', 'offline', 'error', 'maintenance', 'unknown')",
            name='valid_ha_instance_status'
        ),
        CheckConstraint(
            "instance_type IN ('family', 'property', 'development', 'test')",
            name='valid_ha_instance_type'
        ),
        CheckConstraint(
            "os_type IN ('ha_os', 'container', 'core', 'supervised') OR os_type IS NULL",
            name='valid_ha_os_type'
        ),
        Index('idx_ha_instances_host', 'host'),
        Index('idx_ha_instances_status', 'status'),
        Index('idx_ha_instances_instance_type', 'instance_type'),
        Index('idx_ha_instances_is_enabled', 'is_enabled'),
        Index('idx_ha_instances_last_seen_at', 'last_seen_at'),
        Index('idx_ha_instances_property_edge_node_id', 'property_edge_node_id'),
        Index('idx_ha_instances_tags', 'tags', postgresql_using='gin'),
    )


class HATerminalSession(Base):
    """
    Track terminal sessions for audit logging and session management.
    Each WebSocket terminal connection creates a session record.
    """
    __tablename__ = "ha_terminal_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    instance_id = Column(GUID, ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False)

    # Session Info
    session_status = Column(String(30), default='active')  # active, disconnected, error
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))

    # User Info
    user_id = Column(String(255), nullable=False)  # Authelia username
    user_ip = Column(INET)  # Client IP address

    # Session Stats
    commands_executed = Column(Integer, default=0)
    bytes_transferred = Column(Integer, default=0)

    # Error Tracking
    disconnect_reason = Column(String(500))

    # Relationships
    instance = relationship("HAInstance", back_populates="terminal_sessions")

    __table_args__ = (
        CheckConstraint(
            "session_status IN ('active', 'disconnected', 'error')",
            name='valid_terminal_session_status'
        ),
        Index('idx_terminal_sessions_instance_id', 'instance_id'),
        Index('idx_terminal_sessions_user_id', 'user_id'),
        Index('idx_terminal_sessions_status', 'session_status'),
        Index('idx_terminal_sessions_started_at', 'started_at'),
    )


class HALogAnalysis(Base):
    """
    Track Claude-powered log analysis requests and results.
    Supports the command approval workflow for AI-suggested fixes.
    """
    __tablename__ = "ha_log_analyses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    instance_id = Column(GUID, ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False)

    # Analysis Request
    question = Column(Text, nullable=False)  # User's natural language question
    additional_instance_ids = Column(JSONB, default=list)  # Other instances to include
    log_types = Column(JSONB, default=list)  # ["home-assistant", "supervisor", "core"]
    time_range_hours = Column(Integer, default=24)  # How far back to look

    # Analysis Status
    analysis_status = Column(String(30), default='pending')  # pending, analyzing, completed, failed

    # Analysis Results
    analysis_text = Column(Text)  # Claude's response
    suggested_commands = Column(JSONB, default=list)  # [{instance: "...", command: "...", reason: "..."}]
    logs_reviewed_count = Column(Integer)  # Number of log lines analyzed

    # Timing
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # User Info
    submitted_by = Column(String(255), nullable=False)  # Authelia username

    # Error Tracking
    error_message = Column(Text)

    # Relationships
    instance = relationship("HAInstance", back_populates="log_analyses")
    command_approvals = relationship("HACommandApproval", back_populates="analysis", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "analysis_status IN ('pending', 'analyzing', 'completed', 'failed')",
            name='valid_log_analysis_status'
        ),
        Index('idx_log_analyses_instance_id', 'instance_id'),
        Index('idx_log_analyses_status', 'analysis_status'),
        Index('idx_log_analyses_submitted_by', 'submitted_by'),
        Index('idx_log_analyses_submitted_at', 'submitted_at'),
    )


class HACommandApproval(Base):
    """
    Track command approval workflow for AI-suggested fixes.
    Commands suggested by Claude require human approval before execution.
    """
    __tablename__ = "ha_command_approvals"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    analysis_id = Column(GUID, ForeignKey('ha_log_analyses.id', ondelete='CASCADE'), nullable=False)

    # Command Info
    target_instance_id = Column(GUID, ForeignKey('ha_instances.id', ondelete='CASCADE'), nullable=False)
    command = Column(Text, nullable=False)  # The command to execute
    reason = Column(Text)  # Why Claude suggested this command

    # Approval Status
    approval_status = Column(String(30), default='pending')  # pending, approved, rejected, executed, failed

    # Approval Decision
    approved_by = Column(String(255))  # Username who approved/rejected
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)  # If rejected, why

    # Execution Results
    executed_at = Column(DateTime(timezone=True))
    execution_output = Column(Text)  # stdout/stderr from command
    exit_code = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("HALogAnalysis", back_populates="command_approvals")
    target_instance = relationship("HAInstance", foreign_keys=[target_instance_id])

    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'executed', 'failed')",
            name='valid_command_approval_status'
        ),
        Index('idx_command_approvals_analysis_id', 'analysis_id'),
        Index('idx_command_approvals_target_instance_id', 'target_instance_id'),
        Index('idx_command_approvals_status', 'approval_status'),
        Index('idx_command_approvals_created_at', 'created_at'),
    )


# Export all models
__all__ = [
    'HAInstance',
    'HATerminalSession',
    'HALogAnalysis',
    'HACommandApproval'
]
