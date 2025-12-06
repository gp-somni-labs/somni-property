"""
Project Phase API Endpoints
REST API for phased project planning and deposit management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from db.database import get_db
from api.schemas_project_phases import (
    ProjectPhase, ProjectPhaseCreate, ProjectPhaseUpdate,
    ProjectPhaseLineItem, ProjectPhaseLineItemCreate, ProjectPhaseLineItemUpdate,
    ProjectPhaseMilestone, ProjectPhaseMilestoneCreate, ProjectPhaseMilestoneUpdate,
    ProjectDeposit, ProjectDepositCreate, ProjectDepositUpdate,
    ProjectTimeline, ProjectTimelineCreate, ProjectTimelineUpdate,
    PhaseGenerationRequest, PhaseGenerationResponse,
    DepositApplicationRequest, DepositApplicationResponse,
    ProjectPhaseProgressSummary, ProjectFinancialReport
)
from services.project_phase_service import ProjectPhaseService
from db.models_project_phases import (
    ProjectPhase as ProjectPhaseModel,
    ProjectPhaseLineItem as ProjectPhaseLineItemModel,
    ProjectPhaseMilestone as ProjectPhaseMilestoneModel,
    ProjectDeposit as ProjectDepositModel,
    ProjectTimeline as ProjectTimelineModel
)
from sqlalchemy import select

router = APIRouter(prefix="/project-phases", tags=["Project Phases"])


# ============================================================================
# PHASE GENERATION & AUTO-PLANNING
# ============================================================================

@router.post("/generate", response_model=PhaseGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_project_phases(
    request: PhaseGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-generate project phases from an existing quote

    This creates a phased project plan with incremental deposits.

    Example:
        - Phase A (Foundation): $15K deposit unlocks basic infrastructure
        - Phase B (Enhancement): $25K deposit unlocks advanced features
        - Phase C (Premium): $40K deposit unlocks premium automation
    """
    service = ProjectPhaseService(db)

    try:
        result = await service.generate_phases_from_quote(
            quote_id=request.quote_id,
            number_of_phases=request.number_of_phases,
            phase_strategy=request.phase_strategy,
            deposit_percentage=request.deposit_percentage_per_phase,
            include_timeline=request.include_timeline,
            average_days_per_phase=request.average_days_per_phase
        )

        return PhaseGenerationResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# DEPOSIT MANAGEMENT
# ============================================================================

@router.post("/deposits/apply", response_model=DepositApplicationResponse)
async def apply_deposit_to_phase(
    request: DepositApplicationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply a deposit to unlock a project phase

    When a customer makes a deposit, this endpoint:
    1. Records the deposit
    2. Updates phase status to 'unlocked' if deposit meets requirement
    3. Updates project timeline
    4. Returns next steps (next phase deposit info)
    """
    service = ProjectPhaseService(db)

    try:
        result = await service.apply_deposit(
            quote_id=request.quote_id,
            phase_id=request.phase_id,
            deposit_amount=request.deposit_amount,
            payment_method=request.payment_method,
            payment_reference=request.payment_reference
        )

        return DepositApplicationResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/deposits/quote/{quote_id}", response_model=List[ProjectDeposit])
async def get_deposits_for_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all deposits for a quote"""
    query = select(ProjectDepositModel).where(ProjectDepositModel.quote_id == quote_id)
    result = await db.execute(query)
    deposits = result.scalars().all()

    return deposits


# ============================================================================
# PROJECT PROGRESS & REPORTING
# ============================================================================

@router.get("/progress/{quote_id}", response_model=ProjectPhaseProgressSummary)
async def get_project_progress(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive project progress summary

    Returns:
        - Financial status (paid vs. remaining)
        - Phase breakdown (planned, unlocked, in progress, completed)
        - Timeline and completion percentage
        - Next steps for customer
    """
    service = ProjectPhaseService(db)

    try:
        progress = await service.get_project_progress(quote_id)
        return ProjectPhaseProgressSummary(**progress)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# PHASE CRUD OPERATIONS
# ============================================================================

@router.get("/quote/{quote_id}", response_model=List[ProjectPhase])
async def get_phases_for_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all phases for a quote, ordered by phase number"""
    query = select(ProjectPhaseModel).where(
        ProjectPhaseModel.quote_id == quote_id
    ).order_by(ProjectPhaseModel.phase_number)

    result = await db.execute(query)
    phases = result.scalars().all()

    return phases


@router.get("/{phase_id}", response_model=ProjectPhase)
async def get_phase(
    phase_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single phase by ID"""
    query = select(ProjectPhaseModel).where(ProjectPhaseModel.id == phase_id)
    result = await db.execute(query)
    phase = result.scalar_one_or_none()

    if not phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")

    return phase


@router.post("/", response_model=ProjectPhase, status_code=status.HTTP_201_CREATED)
async def create_phase(
    phase: ProjectPhaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project phase manually"""
    db_phase = ProjectPhaseModel(**phase.model_dump())

    db.add(db_phase)
    await db.commit()
    await db.refresh(db_phase)

    return db_phase


@router.patch("/{phase_id}", response_model=ProjectPhase)
async def update_phase(
    phase_id: UUID,
    phase_update: ProjectPhaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a project phase"""
    query = select(ProjectPhaseModel).where(ProjectPhaseModel.id == phase_id)
    result = await db.execute(query)
    db_phase = result.scalar_one_or_none()

    if not db_phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")

    # Update fields
    update_data = phase_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_phase, field, value)

    await db.commit()
    await db.refresh(db_phase)

    return db_phase


@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phase(
    phase_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project phase"""
    query = select(ProjectPhaseModel).where(ProjectPhaseModel.id == phase_id)
    result = await db.execute(query)
    db_phase = result.scalar_one_or_none()

    if not db_phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")

    await db.delete(db_phase)
    await db.commit()


# ============================================================================
# PHASE LINE ITEMS
# ============================================================================

@router.get("/{phase_id}/line-items", response_model=List[ProjectPhaseLineItem])
async def get_phase_line_items(
    phase_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all line items for a phase"""
    query = select(ProjectPhaseLineItemModel).where(
        ProjectPhaseLineItemModel.phase_id == phase_id
    ).order_by(ProjectPhaseLineItemModel.line_number)

    result = await db.execute(query)
    items = result.scalars().all()

    return items


@router.post("/{phase_id}/line-items", response_model=ProjectPhaseLineItem, status_code=status.HTTP_201_CREATED)
async def create_phase_line_item(
    phase_id: UUID,
    item: ProjectPhaseLineItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a line item to a phase"""
    # Verify phase exists
    phase_query = select(ProjectPhaseModel).where(ProjectPhaseModel.id == phase_id)
    phase_result = await db.execute(phase_query)
    if not phase_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")

    db_item = ProjectPhaseLineItemModel(**item.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    return db_item


# ============================================================================
# PHASE MILESTONES
# ============================================================================

@router.get("/{phase_id}/milestones", response_model=List[ProjectPhaseMilestone])
async def get_phase_milestones(
    phase_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all milestones for a phase"""
    query = select(ProjectPhaseMilestoneModel).where(
        ProjectPhaseMilestoneModel.phase_id == phase_id
    ).order_by(ProjectPhaseMilestoneModel.milestone_order)

    result = await db.execute(query)
    milestones = result.scalars().all()

    return milestones


@router.post("/{phase_id}/milestones", response_model=ProjectPhaseMilestone, status_code=status.HTTP_201_CREATED)
async def create_phase_milestone(
    phase_id: UUID,
    milestone: ProjectPhaseMilestoneCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a milestone to a phase"""
    # Verify phase exists
    phase_query = select(ProjectPhaseModel).where(ProjectPhaseModel.id == phase_id)
    phase_result = await db.execute(phase_query)
    if not phase_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")

    db_milestone = ProjectPhaseMilestoneModel(**milestone.model_dump())
    db.add(db_milestone)
    await db.commit()
    await db.refresh(db_milestone)

    return db_milestone


@router.patch("/milestones/{milestone_id}", response_model=ProjectPhaseMilestone)
async def update_milestone(
    milestone_id: UUID,
    milestone_update: ProjectPhaseMilestoneUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a milestone (e.g., mark as completed, add notes)"""
    query = select(ProjectPhaseMilestoneModel).where(ProjectPhaseMilestoneModel.id == milestone_id)
    result = await db.execute(query)
    db_milestone = result.scalar_one_or_none()

    if not db_milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    # Update fields
    update_data = milestone_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_milestone, field, value)

    await db.commit()
    await db.refresh(db_milestone)

    return db_milestone


# ============================================================================
# PROJECT TIMELINE
# ============================================================================

@router.get("/timeline/{quote_id}", response_model=ProjectTimeline)
async def get_project_timeline(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get project timeline for a quote"""
    query = select(ProjectTimelineModel).where(ProjectTimelineModel.quote_id == quote_id)
    result = await db.execute(query)
    timeline = result.scalar_one_or_none()

    if not timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")

    return timeline


@router.patch("/timeline/{timeline_id}", response_model=ProjectTimeline)
async def update_project_timeline(
    timeline_id: UUID,
    timeline_update: ProjectTimelineUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project timeline"""
    query = select(ProjectTimelineModel).where(ProjectTimelineModel.id == timeline_id)
    result = await db.execute(query)
    db_timeline = result.scalar_one_or_none()

    if not db_timeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline not found")

    # Update fields
    update_data = timeline_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_timeline, field, value)

    await db.commit()
    await db.refresh(db_timeline)

    return db_timeline
