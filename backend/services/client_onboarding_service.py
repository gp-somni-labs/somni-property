"""
Client Onboarding Service
Manages the client onboarding workflow and progress tracking
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from db.models import Client
from api.schemas import ClientUpdate

logger = logging.getLogger(__name__)


class ClientOnboardingService:
    """
    Service for managing client onboarding workflow

    Onboarding Stages:
    1. initial - Client record created, basic info collected
    2. discovery - Discovery call scheduled/completed, initial assessment
    3. assessment - Property assessment, requirements gathering
    4. proposal - Service proposal created and presented
    5. contract - Contract negotiation and signing
    6. deployment - Infrastructure deployment and setup
    7. completed - Onboarding complete, client active

    Responsibilities:
    - Track onboarding progress
    - Validate stage transitions
    - Calculate completion percentage
    - Manage discovery call scheduling
    - Handle onboarding completion
    """

    # Onboarding stage definitions
    STAGES = [
        'initial',
        'discovery',
        'assessment',
        'proposal',
        'contract',
        'deployment',
        'completed'
    ]

    # Stage to progress percentage mapping
    STAGE_PROGRESS = {
        'initial': 0,
        'discovery': 15,
        'assessment': 30,
        'proposal': 50,
        'contract': 70,
        'deployment': 85,
        'completed': 100
    }

    # Required fields for each stage completion
    STAGE_REQUIREMENTS = {
        'initial': [
            'name', 'email', 'tier', 'client_type'
        ],
        'discovery': [
            'name', 'email', 'tier', 'client_type',
            'primary_contact_name', 'primary_contact_email',
            'discovery_call_completed_at'
        ],
        'assessment': [
            'name', 'email', 'tier', 'client_type',
            'primary_contact_name', 'primary_contact_email',
            'discovery_call_completed_at',
            'property_name', 'property_city', 'property_state',
            'initial_assessment_completed'
        ],
        'proposal': [
            'name', 'email', 'tier', 'client_type',
            'primary_contact_name', 'primary_contact_email',
            'property_name', 'property_city', 'property_state',
            'subscription_plan', 'monthly_fee'
        ],
        'contract': [
            'name', 'email', 'tier', 'client_type',
            'primary_contact_name', 'primary_contact_email',
            'property_name', 'property_city', 'property_state',
            'subscription_plan', 'monthly_fee',
            'support_level'
        ],
        'deployment': [
            'name', 'email', 'tier', 'client_type',
            'subscription_plan', 'monthly_fee', 'support_level'
        ],
        'completed': []  # All previous requirements must be met
    }

    def __init__(self, db: AsyncSession):
        """Initialize service with database session"""
        self.db = db

    async def get_client(self, client_id: UUID) -> Optional[Client]:
        """Get client by ID"""
        query = select(Client).where(Client.id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def advance_stage(
        self,
        client_id: UUID,
        validate: bool = True
    ) -> Client:
        """
        Advance client to next onboarding stage

        Args:
            client_id: Client UUID
            validate: If True, validate requirements before advancing

        Returns:
            Updated client

        Raises:
            HTTPException if validation fails or stage transition invalid
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        current_stage = client.onboarding_stage
        current_index = self.STAGES.index(current_stage)

        # Check if already at final stage
        if current_stage == 'completed':
            raise HTTPException(
                status_code=400,
                detail="Client onboarding already completed"
            )

        # Validate requirements if requested
        if validate:
            validation = self.validate_stage_requirements(client, current_stage)
            if not validation['is_valid']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot advance stage. Missing required fields: {', '.join(validation['missing_fields'])}"
                )

        # Advance to next stage
        next_stage = self.STAGES[current_index + 1]
        client.onboarding_stage = next_stage
        client.onboarding_step = 1
        client.onboarding_progress_percent = self.STAGE_PROGRESS[next_stage]

        # Mark onboarding as completed if reaching final stage
        if next_stage == 'completed':
            client.onboarding_completed = True
            client.onboarded_at = datetime.utcnow()
            client.status = 'active'

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Client {client_id} advanced from {current_stage} to {next_stage}")
        return client

    async def set_stage(
        self,
        client_id: UUID,
        stage: str,
        validate: bool = False
    ) -> Client:
        """
        Set client to specific onboarding stage (admin override)

        Args:
            client_id: Client UUID
            stage: Target stage
            validate: If True, validate requirements

        Returns:
            Updated client

        Raises:
            HTTPException if validation fails or stage invalid
        """
        if stage not in self.STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage. Must be one of: {', '.join(self.STAGES)}"
            )

        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Validate requirements if requested
        if validate:
            validation = self.validate_stage_requirements(client, stage)
            if not validation['is_valid']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set stage. Missing required fields: {', '.join(validation['missing_fields'])}"
                )

        old_stage = client.onboarding_stage
        client.onboarding_stage = stage
        client.onboarding_progress_percent = self.STAGE_PROGRESS[stage]

        # Mark onboarding as completed if setting to final stage
        if stage == 'completed':
            client.onboarding_completed = True
            client.onboarded_at = datetime.utcnow()
            client.status = 'active'

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Client {client_id} stage changed from {old_stage} to {stage}")
        return client

    def validate_stage_requirements(
        self,
        client: Client,
        stage: str
    ) -> Dict[str, Any]:
        """
        Validate that client meets requirements for a stage

        Args:
            client: Client model
            stage: Stage to validate

        Returns:
            Dict with:
                - is_valid: bool
                - missing_fields: List[str]
                - completion_percent: int
        """
        required_fields = self.STAGE_REQUIREMENTS.get(stage, [])
        missing_fields = []

        for field in required_fields:
            value = getattr(client, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0
        completion_percent = 0 if not required_fields else int(
            ((len(required_fields) - len(missing_fields)) / len(required_fields)) * 100
        )

        return {
            'is_valid': is_valid,
            'missing_fields': missing_fields,
            'required_fields': required_fields,
            'completion_percent': completion_percent
        }

    async def schedule_discovery_call(
        self,
        client_id: UUID,
        scheduled_at: datetime
    ) -> Client:
        """
        Schedule discovery call for client

        Args:
            client_id: Client UUID
            scheduled_at: Scheduled datetime

        Returns:
            Updated client
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client.discovery_call_scheduled_at = scheduled_at

        # Advance to discovery stage if still in initial
        if client.onboarding_stage == 'initial':
            client.onboarding_stage = 'discovery'
            client.onboarding_progress_percent = self.STAGE_PROGRESS['discovery']

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Discovery call scheduled for client {client_id} at {scheduled_at}")
        return client

    async def complete_discovery_call(
        self,
        client_id: UUID,
        transcript: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Client:
        """
        Mark discovery call as completed

        Args:
            client_id: Client UUID
            transcript: Optional call transcript
            notes: Optional notes from call

        Returns:
            Updated client
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client.discovery_call_completed_at = datetime.utcnow()

        if transcript:
            client.discovery_call_transcript = transcript

        if notes:
            client.initial_notes = notes

        # Ensure we're at least in discovery stage
        if client.onboarding_stage == 'initial':
            client.onboarding_stage = 'discovery'
            client.onboarding_progress_percent = self.STAGE_PROGRESS['discovery']

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Discovery call completed for client {client_id}")
        return client

    async def complete_initial_assessment(
        self,
        client_id: UUID,
        assessment_notes: Optional[str] = None
    ) -> Client:
        """
        Mark initial assessment as completed

        Args:
            client_id: Client UUID
            assessment_notes: Optional assessment notes

        Returns:
            Updated client
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client.initial_assessment_completed = True

        if assessment_notes:
            if client.initial_notes:
                client.initial_notes += f"\n\nAssessment Notes:\n{assessment_notes}"
            else:
                client.initial_notes = assessment_notes

        # Progress to assessment stage if in earlier stages
        stage_index = self.STAGES.index(client.onboarding_stage)
        assessment_index = self.STAGES.index('assessment')
        if stage_index < assessment_index:
            client.onboarding_stage = 'assessment'
            client.onboarding_progress_percent = self.STAGE_PROGRESS['assessment']

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Initial assessment completed for client {client_id}")
        return client

    async def get_onboarding_progress(self, client_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive onboarding progress information

        Returns:
            Dict with stage, progress, validation, next steps, etc.
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        current_stage = client.onboarding_stage
        current_index = self.STAGES.index(current_stage)

        # Validate current stage requirements
        current_validation = self.validate_stage_requirements(client, current_stage)

        # Determine next stage
        next_stage = None
        next_stage_requirements = []
        if current_index < len(self.STAGES) - 1:
            next_stage = self.STAGES[current_index + 1]
            next_stage_requirements = self.STAGE_REQUIREMENTS.get(next_stage, [])

        # Build progress info
        return {
            'client_id': str(client.id),
            'client_name': client.name,
            'current_stage': current_stage,
            'current_step': client.onboarding_step,
            'progress_percent': client.onboarding_progress_percent,
            'onboarding_completed': client.onboarding_completed,
            'onboarded_at': client.onboarded_at.isoformat() if client.onboarded_at else None,
            'current_stage_validation': current_validation,
            'next_stage': next_stage,
            'next_stage_requirements': next_stage_requirements,
            'discovery_call_scheduled_at': client.discovery_call_scheduled_at.isoformat() if client.discovery_call_scheduled_at else None,
            'discovery_call_completed_at': client.discovery_call_completed_at.isoformat() if client.discovery_call_completed_at else None,
            'initial_assessment_completed': client.initial_assessment_completed,
            'stages': self.STAGES,
            'stage_progress_map': self.STAGE_PROGRESS
        }

    async def update_onboarding_step(
        self,
        client_id: UUID,
        step: int
    ) -> Client:
        """
        Update current step within onboarding stage

        Args:
            client_id: Client UUID
            step: Step number (1-based)

        Returns:
            Updated client
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if step < 1:
            raise HTTPException(status_code=400, detail="Step must be >= 1")

        client.onboarding_step = step
        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Client {client_id} onboarding step updated to {step}")
        return client


def get_client_onboarding_service(db: AsyncSession) -> ClientOnboardingService:
    """Get ClientOnboardingService instance"""
    return ClientOnboardingService(db)
