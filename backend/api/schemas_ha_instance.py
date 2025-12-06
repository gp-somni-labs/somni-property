"""
Home Assistant Instance API Schemas
Pydantic models for HA Instance management endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


# ============================================================================
# HA INSTANCE SCHEMAS
# ============================================================================

class HAInstanceBase(BaseModel):
    """Base schema for HA Instance"""
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    host: str = Field(..., min_length=1, max_length=255, description="Tailscale IP (100.x.x.x)")
    port: int = Field(default=8123, ge=1, le=65535, description="HA web UI port")
    location: Optional[str] = Field(None, max_length=255, description="Physical location")
    description: Optional[str] = Field(None, description="Additional notes")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")

    # SSH Configuration
    ssh_port: int = Field(default=22, ge=1, le=65535, description="SSH port")
    ssh_user: str = Field(default="root", max_length=100, description="SSH username")
    ssh_key_name: Optional[str] = Field(None, max_length=255, description="SSH key secret name")

    # Home Assistant API
    ha_api_url: Optional[str] = Field(None, max_length=500, description="HA API URL")

    # Instance Type
    instance_type: str = Field(
        default="family",
        pattern="^(family|property|development|test)$",
        description="Instance type"
    )

    # Property Link (optional)
    property_edge_node_id: Optional[UUID] = Field(None, description="Link to PropertyEdgeNode")

    # Enabled
    is_enabled: bool = Field(default=True, description="Is instance enabled")


class HAInstanceCreate(HAInstanceBase):
    """Schema for creating a new HA Instance"""
    ha_api_token: Optional[str] = Field(None, description="Long-lived access token (will be encrypted)")


class HAInstanceUpdate(BaseModel):
    """Schema for updating an HA Instance"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    ssh_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_user: Optional[str] = Field(None, max_length=100)
    ssh_key_name: Optional[str] = Field(None, max_length=255)

    ha_api_url: Optional[str] = Field(None, max_length=500)
    ha_api_token: Optional[str] = Field(None, description="New API token (will be encrypted)")

    instance_type: Optional[str] = Field(None, pattern="^(family|property|development|test)$")
    property_edge_node_id: Optional[UUID] = None
    is_enabled: Optional[bool] = None


class HAInstanceStatus(BaseModel):
    """HA Instance status check result"""
    online: bool
    ha_version: Optional[str] = None
    supervisor_version: Optional[str] = None
    os_type: Optional[str] = None
    uptime_seconds: Optional[int] = None
    healthy: bool = False
    last_checked: datetime
    error: Optional[str] = None


class HAInstanceResponse(HAInstanceBase):
    """HA Instance response with all fields"""
    id: UUID
    status: str = Field(default="unknown", description="Current status")
    last_seen_at: Optional[datetime] = None
    last_status_check_at: Optional[datetime] = None
    status_message: Optional[str] = None

    # HA Info
    ha_version: Optional[str] = None
    supervisor_version: Optional[str] = None
    os_type: Optional[str] = None
    uptime_seconds: Optional[int] = None

    # Component Tracking
    installed_somni_components: Dict[str, bool] = Field(default_factory=dict)
    last_component_sync_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HAInstanceListResponse(BaseModel):
    """Paginated HA Instance list response"""
    items: List[HAInstanceResponse]
    total: int
    skip: int
    limit: int


class HAInstanceBulkStatusRequest(BaseModel):
    """Request to check status of multiple instances"""
    instance_ids: List[UUID] = Field(..., min_length=1, max_length=50)


class HAInstanceBulkStatusResponse(BaseModel):
    """Status check results for multiple instances"""
    results: Dict[str, HAInstanceStatus]
    checked_at: datetime


# ============================================================================
# TERMINAL SESSION SCHEMAS
# ============================================================================

class HATerminalSessionResponse(BaseModel):
    """Terminal session info"""
    id: UUID
    instance_id: UUID
    session_status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    user_id: str
    commands_executed: int = 0
    bytes_transferred: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# LOG ANALYSIS SCHEMAS
# ============================================================================

class HALogAnalysisRequest(BaseModel):
    """Request to analyze logs"""
    question: str = Field(..., min_length=10, max_length=2000, description="Natural language question")
    additional_instance_ids: List[UUID] = Field(default_factory=list, description="Other instances to include")
    log_types: List[str] = Field(
        default_factory=lambda: ["home-assistant"],
        description="Log types to analyze"
    )
    time_range_hours: int = Field(default=24, ge=1, le=168, description="Hours of logs to analyze")


class HALogAnalysisResponse(BaseModel):
    """Log analysis result"""
    id: UUID
    instance_id: UUID
    question: str
    analysis_status: str
    analysis_text: Optional[str] = None
    suggested_commands: List[Dict[str, Any]] = Field(default_factory=list)
    logs_reviewed_count: Optional[int] = None
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    submitted_by: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HALogAnalysisListResponse(BaseModel):
    """Paginated log analysis list"""
    items: List[HALogAnalysisResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# COMMAND APPROVAL SCHEMAS
# ============================================================================

class HACommandApprovalRequest(BaseModel):
    """Request to approve/reject a command"""
    approved: bool = Field(..., description="Whether to approve the command")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class HACommandApprovalResponse(BaseModel):
    """Command approval info"""
    id: UUID
    analysis_id: UUID
    target_instance_id: UUID
    command: str
    reason: Optional[str] = None
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_output: Optional[str] = None
    exit_code: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HAPendingCommandsResponse(BaseModel):
    """List of pending commands awaiting approval"""
    commands: List[HACommandApprovalResponse]
    total_pending: int
