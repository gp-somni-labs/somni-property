"""
Somni Property Manager - Leads API
CRUD endpoints for lead management and NoteCaptureMCP integration.

This API provides:
1. Standard CRUD operations for leads
2. Special endpoint for NoteCaptureMCP integration
3. Lead activity tracking
4. Lead-to-client conversion
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

from db.database import get_db
from db.models_leads import Lead as LeadModel, LeadActivity as LeadActivityModel
from db.models import Client as ClientModel
from api.schemas_leads import (
    Lead, LeadCreate, LeadUpdate, LeadListResponse,
    LeadActivity, LeadActivityCreate,
    NoteCaptureLead, NoteCaptureleadResponse
)
from core.auth import AuthUser, require_manager, get_optional_auth_user
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# NOTECAPTURE INTEGRATION ENDPOINT (API Key Auth)
# ============================================================================

def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> bool:
    """
    Verify API key for NoteCaptureMCP integration.

    NoteCaptureMCP uses API key auth, not employee SSO.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Check against configured API key
    expected_key = getattr(settings, 'NOTECAPTURE_API_KEY', None)
    if not expected_key:
        # If no key configured, accept any key in development
        if settings.DEBUG:
            return True
        raise HTTPException(status_code=503, detail="NoteCaptureMCP integration not configured")

    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@router.post("/notecapture", response_model=NoteCaptureleadResponse, tags=["notecapture-integration"])
async def create_lead_from_notecapture(
    lead_data: NoteCaptureLead,
    db: AsyncSession = Depends(get_db),
    _api_key_valid: bool = Depends(verify_api_key)
):
    """
    Create a lead from NoteCaptureMCP.

    This endpoint is called by NoteCaptureMCP when a business opportunity
    is detected in a captured conversation (Omi/Limitless pendant).

    Authentication: X-API-Key header

    The lead will be created with:
    - Contact information extracted from conversation
    - Property interest details
    - AI-generated summary and key points
    - Business signals and confidence scores
    - Link back to Obsidian note
    """
    try:
        # Calculate initial lead score based on business signals
        score = 50  # Base score
        interest_level = 'medium'

        if lead_data.business_signals:
            # Higher score for more/stronger signals
            signal_boost = 0
            for signal in lead_data.business_signals:
                confidence = signal.get('confidence', 0.5)
                signal_type = signal.get('type', '')

                if signal_type in ['potential_lead', 'service_inquiry']:
                    signal_boost += int(20 * confidence)
                elif signal_type == 'property_interest':
                    signal_boost += int(15 * confidence)
                else:
                    signal_boost += int(10 * confidence)

            score = min(100, 50 + signal_boost)

            # Determine interest level
            if score >= 80:
                interest_level = 'high'
            elif score >= 60:
                interest_level = 'medium'
            else:
                interest_level = 'low'

        # Create lead
        lead = LeadModel(
            name=lead_data.name,
            email=lead_data.email,
            phone=lead_data.phone,
            company=lead_data.company,
            source='notecapture',
            source_id=lead_data.source_id,
            obsidian_note_path=lead_data.obsidian_path,
            property_type=lead_data.property_type,
            property_location=lead_data.property_location,
            property_details=lead_data.property_interest,
            interest_level=interest_level,
            status='new',
            score=score,
            summary=lead_data.summary,
            key_points=lead_data.key_points,
            action_items=lead_data.action_items,
            metadata={
                'business_signals': lead_data.business_signals,
                'capture_timestamp': lead_data.capture_timestamp.isoformat() if lead_data.capture_timestamp else None,
                'has_raw_content': bool(lead_data.raw_content),
            }
        )

        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        # Create initial activity
        activity = LeadActivityModel(
            lead_id=lead.id,
            activity_type='note',
            description=f"Lead created from NoteCaptureMCP conversation. {len(lead_data.business_signals)} business signals detected.",
            performed_by='NoteCaptureMCP'
        )
        db.add(activity)
        await db.commit()

        logger.info(f"Created lead {lead.id} from NoteCaptureMCP: {lead.name} (score: {score})")

        return NoteCaptureleadResponse(
            status='success',
            lead_id=lead.id,
            message=f"Lead created successfully with score {score}",
            external_id=str(lead.id)
        )

    except Exception as e:
        logger.error(f"Failed to create lead from NoteCaptureMCP: {e}", exc_info=True)
        await db.rollback()
        return NoteCaptureleadResponse(
            status='error',
            message=f"Failed to create lead: {str(e)}",
            lead_id=None,
            external_id=None
        )


# ============================================================================
# STANDARD CRUD ENDPOINTS
# ============================================================================

@router.post("", response_model=Lead, status_code=201)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Create a new lead manually.

    Requires: Manager or Admin role
    """
    lead = LeadModel(**lead_data.model_dump())
    db.add(lead)
    await db.flush()
    await db.refresh(lead)

    # Create activity
    activity = LeadActivityModel(
        lead_id=lead.id,
        activity_type='note',
        description=f"Lead created manually by {auth_user.username}",
        performed_by=auth_user.username
    )
    db.add(activity)
    await db.commit()

    return lead


@router.get("", response_model=LeadListResponse)
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, pattern="^(new|contacted|qualified|proposal|negotiation|converted|lost)$"),
    source: Optional[str] = Query(None, pattern="^(notecapture|website|referral|manual|import|other)$"),
    interest_level: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    search: Optional[str] = Query(None, description="Search by name, email, company"),
    assigned_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List leads with filtering and pagination.

    Filters:
    - status: Lead status
    - source: Lead source (notecapture, website, etc.)
    - interest_level: Interest level (low, medium, high)
    - min_score: Minimum lead score
    - search: Search by name, email, or company
    - assigned_to: Filter by assigned employee

    Requires: Manager or Admin role
    """
    query = select(LeadModel)

    # Apply filters
    if status:
        query = query.where(LeadModel.status == status)
    if source:
        query = query.where(LeadModel.source == source)
    if interest_level:
        query = query.where(LeadModel.interest_level == interest_level)
    if min_score is not None:
        query = query.where(LeadModel.score >= min_score)
    if assigned_to:
        query = query.where(LeadModel.assigned_to == assigned_to)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (LeadModel.name.ilike(search_pattern)) |
            (LeadModel.email.ilike(search_pattern)) |
            (LeadModel.company.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get leads with pagination, sorted by score (highest first), then by created_at
    query = query.order_by(LeadModel.score.desc(), LeadModel.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    leads = result.scalars().all()

    return LeadListResponse(
        total=total,
        items=leads,
        skip=skip,
        limit=limit
    )


@router.get("/{lead_id}", response_model=Lead)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific lead by ID."""
    query = select(LeadModel).where(LeadModel.id == lead_id)
    result = await db.execute(query)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.put("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update a lead."""
    query = select(LeadModel).where(LeadModel.id == lead_id)
    result = await db.execute(query)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Track status changes
    old_status = lead.status
    update_data = lead_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(lead, key, value)

    lead.updated_at = datetime.utcnow()

    # Update last_activity_at
    lead.last_activity_at = datetime.utcnow()

    # Create activity for status change
    if 'status' in update_data and update_data['status'] != old_status:
        activity = LeadActivityModel(
            lead_id=lead.id,
            activity_type='status_change',
            description=f"Status changed from {old_status} to {update_data['status']}",
            performed_by=auth_user.username
        )
        db.add(activity)

    await db.flush()
    await db.refresh(lead)
    await db.commit()

    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a lead."""
    query = select(LeadModel).where(LeadModel.id == lead_id)
    result = await db.execute(query)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)
    await db.commit()

    return None


# ============================================================================
# LEAD ACTIVITIES
# ============================================================================

@router.get("/{lead_id}/activities", response_model=List[LeadActivity])
async def get_lead_activities(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get all activities for a lead."""
    # Verify lead exists
    lead_query = select(LeadModel).where(LeadModel.id == lead_id)
    lead_result = await db.execute(lead_query)
    if not lead_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get activities
    query = select(LeadActivityModel).where(
        LeadActivityModel.lead_id == lead_id
    ).order_by(LeadActivityModel.created_at.desc())

    result = await db.execute(query)
    activities = result.scalars().all()

    return activities


@router.post("/{lead_id}/activities", response_model=LeadActivity, status_code=201)
async def create_lead_activity(
    lead_id: UUID,
    activity_data: LeadActivityCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Create a new activity for a lead."""
    # Verify lead exists
    lead_query = select(LeadModel).where(LeadModel.id == lead_id)
    lead_result = await db.execute(lead_query)
    lead = lead_result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Create activity
    activity = LeadActivityModel(
        lead_id=lead_id,
        **activity_data.model_dump(),
        performed_by=activity_data.performed_by or auth_user.username
    )
    db.add(activity)

    # Update lead timestamps
    lead.last_activity_at = datetime.utcnow()
    if activity_data.activity_type in ['call', 'email', 'meeting']:
        lead.contacted_at = datetime.utcnow()

    await db.flush()
    await db.refresh(activity)
    await db.commit()

    return activity


# ============================================================================
# LEAD CONVERSION
# ============================================================================

@router.post("/{lead_id}/convert", response_model=Lead)
async def convert_lead_to_client(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Convert a qualified lead to a client.

    This will:
    1. Create a new Client record
    2. Update the lead status to 'converted'
    3. Link the lead to the new client
    """
    # Get lead
    query = select(LeadModel).where(LeadModel.id == lead_id)
    result = await db.execute(query)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status == 'converted':
        raise HTTPException(status_code=400, detail="Lead already converted")

    # Create client
    client = ClientModel(
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        status='active',
        tier='tier_2',  # Default tier for new clients
        billing_status='active',
        notes=f"Converted from lead. Original source: {lead.source}. Summary: {lead.summary or 'N/A'}"
    )
    db.add(client)
    await db.flush()

    # Update lead
    lead.status = 'converted'
    lead.converted_to_client_id = client.id
    lead.converted_at = datetime.utcnow()
    lead.last_activity_at = datetime.utcnow()

    # Create activity
    activity = LeadActivityModel(
        lead_id=lead.id,
        activity_type='status_change',
        description=f"Lead converted to client {client.id}",
        outcome='positive',
        performed_by=auth_user.username
    )
    db.add(activity)

    await db.commit()
    await db.refresh(lead)

    logger.info(f"Converted lead {lead.id} to client {client.id}")

    return lead


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/stats/summary")
async def get_leads_summary(
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get leads summary statistics."""
    # Total leads by status
    status_query = select(
        LeadModel.status,
        func.count(LeadModel.id).label('count')
    ).group_by(LeadModel.status)
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result}

    # Total leads by source
    source_query = select(
        LeadModel.source,
        func.count(LeadModel.id).label('count')
    ).group_by(LeadModel.source)
    source_result = await db.execute(source_query)
    by_source = {row.source: row.count for row in source_result}

    # Average score
    avg_score_query = select(func.avg(LeadModel.score))
    avg_result = await db.execute(avg_score_query)
    avg_score = avg_result.scalar_one() or 0

    # High-value leads (score >= 70)
    high_value_query = select(func.count(LeadModel.id)).where(LeadModel.score >= 70)
    high_value_result = await db.execute(high_value_query)
    high_value_count = high_value_result.scalar_one()

    # Leads needing follow-up (no activity in 7 days)
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stale_query = select(func.count(LeadModel.id)).where(
        (LeadModel.status.in_(['new', 'contacted', 'qualified'])) &
        ((LeadModel.last_activity_at < seven_days_ago) | (LeadModel.last_activity_at.is_(None)))
    )
    stale_result = await db.execute(stale_query)
    stale_count = stale_result.scalar_one()

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_source": by_source,
        "average_score": round(float(avg_score), 1),
        "high_value_leads": high_value_count,
        "needs_follow_up": stale_count,
        "conversion_rate": round(
            by_status.get('converted', 0) / max(sum(by_status.values()), 1) * 100, 1
        )
    }
