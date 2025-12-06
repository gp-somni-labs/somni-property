"""
Client Projects API Endpoints
View quotes, phases, and progress from client's perspective
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from uuid import UUID

from db.database import get_db
from db.models_quotes import Quote
from db.models_project_phases import (
    ProjectPhase as ProjectPhaseModel,
    ProjectTimeline as ProjectTimelineModel,
    ProjectDeposit as ProjectDepositModel,
    ContractorBid as ContractorBidModel
)
from db.models import Client, Property, Building
from api.schemas_project_phases import (
    ProjectPhase, ProjectTimeline, ProjectDeposit,
    ProjectPhaseProgressSummary
)
from services.project_phase_service import ProjectPhaseService

router = APIRouter(prefix="/client-projects", tags=["Client Projects"])


# ============================================================================
# CLIENT-CENTRIC PROJECT VIEWS
# ============================================================================

@router.get("/clients/{client_id}/projects", response_model=List[dict])
async def get_client_projects(
    client_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status: draft, sent, accepted, in_progress, completed"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects (quotes + phases) for a specific client

    Returns comprehensive view of all quotes and their associated
    project phases, timelines, and financial status.
    """

    # Verify client exists
    client_query = select(Client).where(Client.id == client_id)
    client_result = await db.execute(client_query)
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Get all quotes for this client
    query = select(Quote).where(
        or_(
            Quote.client_id == client_id,
            Quote.converted_to_client_id == client_id
        )
    )

    if status:
        query = query.where(Quote.status == status)

    query = query.order_by(Quote.created_at.desc())

    result = await db.execute(query)
    quotes = result.scalars().all()

    # Build comprehensive project list
    projects = []

    for quote in quotes:
        # Get timeline
        timeline_query = select(ProjectTimelineModel).where(ProjectTimelineModel.quote_id == quote.id)
        timeline_result = await db.execute(timeline_query)
        timeline = timeline_result.scalar_one_or_none()

        # Get phases
        phases_query = select(ProjectPhaseModel).where(
            ProjectPhaseModel.quote_id == quote.id
        ).order_by(ProjectPhaseModel.phase_number)
        phases_result = await db.execute(phases_query)
        phases = list(phases_result.scalars().all())

        # Get deposits
        deposits_query = select(ProjectDepositModel).where(ProjectDepositModel.quote_id == quote.id)
        deposits_result = await db.execute(deposits_query)
        deposits = list(deposits_result.scalars().all())

        # Calculate summary
        total_paid = sum(d.deposit_amount for d in deposits)
        total_value = quote.monthly_total + (quote.hardware_costs or 0) + (quote.setup_fees or 0)

        project = {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "quote_status": quote.status,
            "customer_name": quote.customer_name,
            "property_id": str(quote.property_id) if quote.property_id else None,
            "building_id": str(quote.building_id) if quote.building_id else None,

            # Financial summary
            "total_project_value": float(total_value),
            "total_paid": float(total_paid),
            "balance_remaining": float(total_value - total_paid),
            "payment_percentage": float((total_paid / total_value * 100) if total_value > 0 else 0),

            # Phase summary
            "total_phases": len(phases),
            "phases_unlocked": sum(1 for p in phases if p.deposit_paid),
            "phases_completed": sum(1 for p in phases if p.status == 'completed'),

            # Timeline
            "timeline": {
                "status": timeline.status if timeline else "planning",
                "completion_percentage": timeline.completion_percentage if timeline else 0,
                "planned_start": timeline.planned_start_date.isoformat() if timeline and timeline.planned_start_date else None,
                "planned_completion": timeline.planned_completion_date.isoformat() if timeline and timeline.planned_completion_date else None,
            } if timeline else None,

            # Dates
            "created_at": quote.created_at.isoformat(),
            "updated_at": quote.updated_at.isoformat(),
        }

        projects.append(project)

    return projects


@router.get("/clients/{client_id}/projects/{quote_id}", response_model=dict)
async def get_client_project_detail(
    client_id: UUID,
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed project information for a specific client project

    Includes all phases, deposits, contractor assignments, and timeline.
    """

    # Verify client owns this quote
    quote_query = select(Quote).where(
        Quote.id == quote_id,
        or_(
            Quote.client_id == client_id,
            Quote.converted_to_client_id == client_id
        )
    )
    result = await db.execute(quote_query)
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or does not belong to this client"
        )

    # Get comprehensive project data using service
    service = ProjectPhaseService(db)
    progress = await service.get_project_progress(quote_id)

    # Add quote details
    project_detail = {
        **progress,
        "quote_number": quote.quote_number,
        "quote_status": quote.status,
        "customer_name": quote.customer_name,
        "customer_email": quote.customer_email,
        "property_id": str(quote.property_id) if quote.property_id else None,
        "building_id": str(quote.building_id) if quote.building_id else None,
        "created_at": quote.created_at.isoformat(),
        "updated_at": quote.updated_at.isoformat(),
    }

    return project_detail


@router.get("/properties/{property_id}/projects", response_model=List[dict])
async def get_property_projects(
    property_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects for a specific property

    Shows all quotes and project phases associated with this property.
    """

    # Verify property exists
    property_query = select(Property).where(Property.id == property_id)
    property_result = await db.execute(property_query)
    property_obj = property_result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Get all quotes for this property
    query = select(Quote).where(Quote.property_id == property_id).order_by(Quote.created_at.desc())
    result = await db.execute(query)
    quotes = result.scalars().all()

    projects = []

    for quote in quotes:
        # Get phase count
        phases_query = select(ProjectPhaseModel).where(ProjectPhaseModel.quote_id == quote.id)
        phases_result = await db.execute(phases_query)
        phases = list(phases_result.scalars().all())

        # Get timeline
        timeline_query = select(ProjectTimelineModel).where(ProjectTimelineModel.quote_id == quote.id)
        timeline_result = await db.execute(timeline_query)
        timeline = timeline_result.scalar_one_or_none()

        project = {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "quote_status": quote.status,
            "customer_name": quote.customer_name,
            "client_id": str(quote.client_id) if quote.client_id else None,
            "total_phases": len(phases),
            "phases_completed": sum(1 for p in phases if p.status == 'completed'),
            "timeline_status": timeline.status if timeline else "planning",
            "completion_percentage": timeline.completion_percentage if timeline else 0,
            "created_at": quote.created_at.isoformat(),
        }

        projects.append(project)

    return projects


@router.get("/buildings/{building_id}/projects", response_model=List[dict])
async def get_building_projects(
    building_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects for a specific building

    Shows all quotes and project phases associated with this building.
    """

    # Verify building exists
    building_query = select(Building).where(Building.id == building_id)
    building_result = await db.execute(building_query)
    building = building_result.scalar_one_or_none()

    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    # Get all quotes for this building
    query = select(Quote).where(Quote.building_id == building_id).order_by(Quote.created_at.desc())
    result = await db.execute(query)
    quotes = result.scalars().all()

    projects = []

    for quote in quotes:
        # Get phase count
        phases_query = select(ProjectPhaseModel).where(ProjectPhaseModel.quote_id == quote.id)
        phases_result = await db.execute(phases_query)
        phases = list(phases_result.scalars().all())

        project = {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "quote_status": quote.status,
            "customer_name": quote.customer_name,
            "total_phases": len(phases),
            "phases_completed": sum(1 for p in phases if p.status == 'completed'),
            "created_at": quote.created_at.isoformat(),
        }

        projects.append(project)

    return projects


@router.get("/clients/{client_id}/financial-summary", response_model=dict)
async def get_client_financial_summary(
    client_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive financial summary for all client projects

    Returns total deposits, total contractor costs, profit margins, etc.
    across all projects for this client.
    """

    # Verify client exists
    client_query = select(Client).where(Client.id == client_id)
    client_result = await db.execute(client_query)
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Get all quotes for this client
    quotes_query = select(Quote).where(
        or_(
            Quote.client_id == client_id,
            Quote.converted_to_client_id == client_id
        )
    )
    quotes_result = await db.execute(quotes_query)
    quotes = list(quotes_result.scalars().all())

    # Initialize totals
    total_quoted_value = 0.0
    total_deposits_received = 0.0
    total_contractor_costs = 0.0
    total_contractor_paid = 0.0

    project_summaries = []

    for quote in quotes:
        # Quote value
        quote_value = float(quote.monthly_total + (quote.hardware_costs or 0) + (quote.setup_fees or 0))
        total_quoted_value += quote_value

        # Deposits
        deposits_query = select(ProjectDepositModel).where(ProjectDepositModel.quote_id == quote.id)
        deposits_result = await db.execute(deposits_query)
        deposits = list(deposits_result.scalars().all())
        deposits_sum = sum(float(d.deposit_amount) for d in deposits)
        total_deposits_received += deposits_sum

        # Contractor costs
        phases_query = select(ProjectPhaseModel).where(ProjectPhaseModel.quote_id == quote.id)
        phases_result = await db.execute(phases_query)
        phases = list(phases_result.scalars().all())

        contractor_costs = sum(float(p.contractor_quote_amount or 0) for p in phases)
        contractor_paid = sum(float(p.contractor_paid_amount or 0) for p in phases)

        total_contractor_costs += contractor_costs
        total_contractor_paid += contractor_paid

        project_summaries.append({
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "quote_status": quote.status,
            "quoted_value": quote_value,
            "deposits_received": deposits_sum,
            "contractor_costs": contractor_costs,
            "contractor_paid": contractor_paid,
            "gross_profit": quote_value - contractor_costs,
            "profit_margin": ((quote_value - contractor_costs) / quote_value * 100) if quote_value > 0 else 0
        })

    # Calculate overall metrics
    gross_profit = total_quoted_value - total_contractor_costs
    profit_margin = (gross_profit / total_quoted_value * 100) if total_quoted_value > 0 else 0
    cash_position = total_deposits_received - total_contractor_paid

    return {
        "client_id": str(client_id),
        "client_name": client.name,
        "total_projects": len(quotes),

        # Financial totals
        "total_quoted_value": total_quoted_value,
        "total_deposits_received": total_deposits_received,
        "total_contractor_costs": total_contractor_costs,
        "total_contractor_paid": total_contractor_paid,
        "contractor_balance_owed": total_contractor_costs - total_contractor_paid,

        # Profitability
        "gross_profit": gross_profit,
        "profit_margin_percent": profit_margin,

        # Cash flow
        "cash_position": cash_position,
        "cash_to_collect": total_quoted_value - total_deposits_received,

        # Project breakdown
        "projects": project_summaries
    }
