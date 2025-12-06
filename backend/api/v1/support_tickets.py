"""
Support Tickets API Endpoints
EPIC I.2: Proactive Outreach Workflow (Alerts → Tickets)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from db.database import get_db
from db.models import SupportTicket, Client, PropertyEdgeNode, Alert
from core.auth import get_auth_user, AuthUser
from core.config import settings
from services.alert_monitor import get_sla_hours

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SupportTicketCreate(BaseModel):
    """Create a support ticket"""
    client_id: Optional[uuid.UUID] = None
    hub_id: Optional[uuid.UUID] = None
    alert_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    severity: str = 'medium'
    title: str
    description: str
    priority: Optional[str] = None


class SupportTicketAssign(BaseModel):
    """Assign ticket to staff"""
    assigned_to: str


class SupportTicketResolve(BaseModel):
    """Resolve a ticket"""
    resolution_notes: str


class SupportTicketResponse(BaseModel):
    """Support ticket response"""
    id: uuid.UUID
    client_id: Optional[uuid.UUID]
    hub_id: Optional[uuid.UUID]
    alert_id: Optional[uuid.UUID]
    category: Optional[str]
    severity: Optional[str]
    title: str
    description: str
    status: str
    priority: Optional[str]
    sla_due_at: Optional[datetime]
    sla_breach: bool
    assigned_to: Optional[str]
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    client_notified: bool
    client_notified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Related data (optional)
    client_name: Optional[str] = None
    hub_hostname: Optional[str] = None
    is_auto_created: bool = False

    class Config:
        from_attributes = True


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/support-tickets", response_model=dict)
async def list_support_tickets(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    client_id: Optional[uuid.UUID] = None,
    hub_id: Optional[uuid.UUID] = None,
    sla_breach: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List support tickets with filters.

    Filters:
    - status: open, in_progress, resolved, closed
    - severity: low, medium, high, critical
    - client_id: Filter by client
    - hub_id: Filter by hub
    - sla_breach: Filter by SLA breach status
    """
    # Build query
    query = select(SupportTicket)
    conditions = []

    if status:
        conditions.append(SupportTicket.status == status)
    if severity:
        conditions.append(SupportTicket.severity == severity)
    if client_id:
        conditions.append(SupportTicket.client_id == client_id)
    if hub_id:
        conditions.append(SupportTicket.hub_id == hub_id)
    if sla_breach is not None:
        conditions.append(SupportTicket.sla_breach == sla_breach)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(SupportTicket)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get tickets
    query = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()

    # Build response with related data
    tickets_data = []
    for ticket in tickets:
        ticket_dict = {
            "id": ticket.id,
            "client_id": ticket.client_id,
            "hub_id": ticket.hub_id,
            "alert_id": ticket.alert_id,
            "category": ticket.category,
            "severity": ticket.severity,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "sla_due_at": ticket.sla_due_at,
            "sla_breach": ticket.sla_breach,
            "assigned_to": ticket.assigned_to,
            "assigned_at": ticket.assigned_at,
            "resolved_at": ticket.resolved_at,
            "resolution_notes": ticket.resolution_notes,
            "client_notified": ticket.client_notified,
            "client_notified_at": ticket.client_notified_at,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "is_auto_created": ticket.alert_id is not None
        }

        # Add client name if available
        if ticket.client_id:
            client_result = await db.execute(
                select(Client).where(Client.id == ticket.client_id)
            )
            client = client_result.scalar()
            if client:
                ticket_dict["client_name"] = client.name

        # Add hub hostname if available
        if ticket.hub_id:
            hub_result = await db.execute(
                select(PropertyEdgeNode).where(PropertyEdgeNode.id == ticket.hub_id)
            )
            hub = hub_result.scalar()
            if hub:
                ticket_dict["hub_hostname"] = hub.hostname

        tickets_data.append(ticket_dict)

    return {
        "total": total,
        "tickets": tickets_data
    }


@router.post("/support-tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new support ticket manually.
    """
    # Calculate SLA due time
    sla_hours = get_sla_hours(ticket_data.severity)
    sla_due_at = datetime.utcnow() + timedelta(hours=sla_hours)

    # Create ticket
    ticket = SupportTicket(
        client_id=ticket_data.client_id,
        hub_id=ticket_data.hub_id,
        alert_id=ticket_data.alert_id,
        category=ticket_data.category,
        severity=ticket_data.severity,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority or ticket_data.severity,
        sla_due_at=sla_due_at,
        status='open'
    )

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return ticket


@router.get("/support-tickets/{ticket_id}", response_model=dict)
async def get_support_ticket(
    ticket_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get support ticket details including related alert.
    """
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    ticket_dict = {
        "id": ticket.id,
        "client_id": ticket.client_id,
        "hub_id": ticket.hub_id,
        "alert_id": ticket.alert_id,
        "category": ticket.category,
        "severity": ticket.severity,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "sla_due_at": ticket.sla_due_at,
        "sla_breach": ticket.sla_breach,
        "assigned_to": ticket.assigned_to,
        "assigned_at": ticket.assigned_at,
        "resolved_at": ticket.resolved_at,
        "resolution_notes": ticket.resolution_notes,
        "client_notified": ticket.client_notified,
        "client_notified_at": ticket.client_notified_at,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "is_auto_created": ticket.alert_id is not None
    }

    # Add client info
    if ticket.client_id:
        client_result = await db.execute(
            select(Client).where(Client.id == ticket.client_id)
        )
        client = client_result.scalar()
        if client:
            ticket_dict["client"] = {
                "id": client.id,
                "name": client.name,
                "email": client.email
            }

    # Add hub info
    if ticket.hub_id:
        hub_result = await db.execute(
            select(PropertyEdgeNode).where(PropertyEdgeNode.id == ticket.hub_id)
        )
        hub = hub_result.scalar()
        if hub:
            ticket_dict["hub"] = {
                "id": hub.id,
                "hostname": hub.hostname,
                "status": hub.status
            }

    # Add alert info if auto-created
    if ticket.alert_id:
        alert_result = await db.execute(
            select(Alert).where(Alert.id == ticket.alert_id)
        )
        alert = alert_result.scalar()
        if alert:
            ticket_dict["alert"] = {
                "id": alert.id,
                "message": alert.message,
                "severity": alert.severity,
                "category": alert.category,
                "occurred_at": alert.occurred_at
            }

    return ticket_dict


@router.patch("/support-tickets/{ticket_id}/assign", response_model=SupportTicketResponse)
async def assign_support_ticket(
    ticket_id: uuid.UUID,
    assign_data: SupportTicketAssign,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a support ticket to a staff member.
    """
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    ticket.assigned_to = assign_data.assigned_to
    ticket.assigned_at = datetime.utcnow()

    # Update status to in_progress if currently open
    if ticket.status == 'open':
        ticket.status = 'in_progress'

    await db.commit()
    await db.refresh(ticket)

    return ticket


@router.patch("/support-tickets/{ticket_id}/resolve", response_model=SupportTicketResponse)
async def resolve_support_ticket(
    ticket_id: uuid.UUID,
    resolve_data: SupportTicketResolve,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a support ticket as resolved.
    """
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    ticket.status = 'resolved'
    ticket.resolved_at = datetime.utcnow()
    ticket.resolution_notes = resolve_data.resolution_notes

    await db.commit()
    await db.refresh(ticket)

    return ticket


@router.patch("/support-tickets/{ticket_id}/close", response_model=SupportTicketResponse)
async def close_support_ticket(
    ticket_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Close a support ticket.
    """
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )

    ticket.status = 'closed'

    await db.commit()
    await db.refresh(ticket)

    return ticket
