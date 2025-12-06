"""
Client Onboarding API Endpoints
Manage client onboarding workflow and progress tracking
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from db.database import get_db
from api.schemas import Client
from services.client_onboarding_service import get_client_onboarding_service, ClientOnboardingService
from services.customer_notification_service import get_customer_notification_service
from core.auth import AuthUser, require_manager, require_admin

router = APIRouter()


# Request/Response schemas for onboarding actions

class AdvanceStageRequest(BaseModel):
    """Request to advance to next onboarding stage"""
    validate: bool = Field(default=True, description="Validate requirements before advancing")


class SetStageRequest(BaseModel):
    """Request to set specific onboarding stage"""
    stage: str = Field(..., pattern="^(initial|discovery|assessment|proposal|contract|deployment|completed)$")
    validate: bool = Field(default=False, description="Validate requirements before setting stage")


class ScheduleDiscoveryCallRequest(BaseModel):
    """Request to schedule discovery call"""
    scheduled_at: datetime = Field(..., description="When the discovery call is scheduled")


class CompleteDiscoveryCallRequest(BaseModel):
    """Request to mark discovery call as completed"""
    transcript: Optional[str] = Field(None, description="Full transcript of discovery call")
    notes: Optional[str] = Field(None, description="Notes from discovery call")


class CompleteAssessmentRequest(BaseModel):
    """Request to mark initial assessment as completed"""
    assessment_notes: Optional[str] = Field(None, description="Assessment notes")


class UpdateStepRequest(BaseModel):
    """Request to update current step within stage"""
    step: int = Field(..., ge=1, description="Step number (1-based)")


class OnboardingProgressResponse(BaseModel):
    """Comprehensive onboarding progress information"""
    client_id: str
    client_name: str
    current_stage: str
    current_step: int
    progress_percent: int
    onboarding_completed: bool
    onboarded_at: Optional[str]
    current_stage_validation: Dict[str, Any]
    next_stage: Optional[str]
    next_stage_requirements: List[str]
    discovery_call_scheduled_at: Optional[str]
    discovery_call_completed_at: Optional[str]
    initial_assessment_completed: bool
    stages: List[str]
    stage_progress_map: Dict[str, int]


# ============================================================================
# ONBOARDING WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/{client_id}/onboarding/advance", response_model=Client)
async def advance_onboarding_stage(
    client_id: UUID,
    request: AdvanceStageRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Advance client to next onboarding stage

    **Stages (in order):**
    1. initial - Client record created
    2. discovery - Discovery call scheduled/completed
    3. assessment - Property assessment completed
    4. proposal - Service proposal presented
    5. contract - Contract signed
    6. deployment - Infrastructure deployed
    7. completed - Onboarding complete

    **Validation:**
    - If validate=true, checks required fields are populated
    - Returns 400 error if requirements not met
    - If validate=false, advances regardless (admin override)
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.advance_stage(
        client_id=client_id,
        validate=request.validate
    )
    await db.commit()
    await db.refresh(client)

    # Send progress update notification
    notification_service = get_customer_notification_service(db)
    try:
        await notification_service.send_progress_update(
            client=client,
            new_stage=client.onboarding_stage,
            progress_percent=client.onboarding_progress_percent,
            channels=['email']
        )
    except Exception as e:
        # Don't fail the request if notification fails
        logger.error(f"Failed to send progress notification: {e}")

    return client


@router.post("/{client_id}/onboarding/set-stage", response_model=Client)
async def set_onboarding_stage(
    client_id: UUID,
    request: SetStageRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Set client to specific onboarding stage (Admin only)

    Useful for:
    - Correcting stage after manual intervention
    - Skipping stages for special cases
    - Moving backwards to re-complete steps
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.set_stage(
        client_id=client_id,
        stage=request.stage,
        validate=request.validate
    )
    await db.commit()
    return client


@router.get("/{client_id}/onboarding/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get comprehensive onboarding progress information

    Returns:
    - Current stage and step
    - Progress percentage
    - Validation status for current stage
    - Missing required fields
    - Next stage and requirements
    - Discovery call status
    - Assessment completion status
    """
    onboarding_service = get_client_onboarding_service(db)
    progress = await onboarding_service.get_onboarding_progress(client_id)
    return OnboardingProgressResponse(**progress)


@router.post("/{client_id}/onboarding/update-step", response_model=Client)
async def update_onboarding_step(
    client_id: UUID,
    request: UpdateStepRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Update current step within onboarding stage

    Steps are stage-specific sub-tasks (e.g., step 1, 2, 3 within "assessment" stage)
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.update_onboarding_step(
        client_id=client_id,
        step=request.step
    )
    await db.commit()
    return client


# ============================================================================
# DISCOVERY CALL ENDPOINTS
# ============================================================================

@router.post("/{client_id}/onboarding/schedule-discovery-call", response_model=Client)
async def schedule_discovery_call(
    client_id: UUID,
    request: ScheduleDiscoveryCallRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Schedule discovery call for client

    - Sets discovery_call_scheduled_at timestamp
    - Advances to 'discovery' stage if still in 'initial'
    - Triggers calendar integration (future enhancement)
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.schedule_discovery_call(
        client_id=client_id,
        scheduled_at=request.scheduled_at
    )
    await db.commit()
    await db.refresh(client)

    # Send discovery call scheduled notification
    notification_service = get_customer_notification_service(db)
    try:
        await notification_service.send_discovery_call_scheduled(
            client=client,
            scheduled_at=request.scheduled_at,
            channels=['email', 'sms']
        )
    except Exception as e:
        # Don't fail the request if notification fails
        logger.error(f"Failed to send discovery call notification: {e}")

    return client


@router.post("/{client_id}/onboarding/complete-discovery-call", response_model=Client)
async def complete_discovery_call(
    client_id: UUID,
    request: CompleteDiscoveryCallRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Mark discovery call as completed

    - Sets discovery_call_completed_at timestamp
    - Stores optional transcript and notes
    - Ensures client is at least in 'discovery' stage
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.complete_discovery_call(
        client_id=client_id,
        transcript=request.transcript,
        notes=request.notes
    )
    await db.commit()
    return client


# ============================================================================
# ASSESSMENT ENDPOINTS
# ============================================================================

@router.post("/{client_id}/onboarding/complete-assessment", response_model=Client)
async def complete_initial_assessment(
    client_id: UUID,
    request: CompleteAssessmentRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Mark initial assessment as completed

    - Sets initial_assessment_completed flag
    - Stores optional assessment notes
    - Progresses to 'assessment' stage if in earlier stages
    """
    onboarding_service = get_client_onboarding_service(db)
    client = await onboarding_service.complete_initial_assessment(
        client_id=client_id,
        assessment_notes=request.assessment_notes
    )
    await db.commit()
    return client
