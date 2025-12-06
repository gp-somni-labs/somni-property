"""
Family Mode API Endpoints
MSP (Managed Service Provider) features for SomniFamily customers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, Integer
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from db.database import get_db
from db.family_models import (
    FamilySubscription, SupportHours, FamilySupportTicket, SupportSession,
    FamilyAlert, FamilyBilling, AutomationTemplate,
    SubscriptionTier, SubscriptionStatus, TicketPriority, TicketStatus,
    AlertSeverity, AlertStatus
)
from core.auth import get_auth_user, AuthUser

router = APIRouter()


# ============================================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================================

@router.get("/family/subscription")
async def get_subscription(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current subscription details for family account"""
    # TODO: Get client_id from auth_user or session
    # For now, return mock data
    return {
        "tier": "pro",
        "status": "active",
        "base_price": 299.00,
        "included_support_hours": 25,
        "next_billing_date": (datetime.utcnow() + timedelta(days=12)).isoformat(),
        "auto_renew": True,
        "addons": [
            {"name": "Extra 10 Support Hours", "price": 450.00},
            {"name": "Priority Alert Monitoring", "price": 50.00}
        ],
        "started_at": "2024-01-15T00:00:00Z"
    }


@router.put("/family/subscription/tier")
async def update_subscription_tier(
    tier: SubscriptionTier,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Update subscription tier"""
    # TODO: Implement tier change logic
    return {"message": f"Subscription tier updated to {tier}", "effective_date": datetime.utcnow().isoformat()}


# ============================================================================
# SUPPORT HOURS ENDPOINTS
# ============================================================================

@router.get("/family/support-hours")
async def get_support_hours(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current billing cycle support hours usage"""
    # TODO: Query actual support hours from database
    return {
        "billing_cycle_start": (datetime.utcnow() - timedelta(days=18)).isoformat(),
        "billing_cycle_end": (datetime.utcnow() + timedelta(days=12)).isoformat(),
        "included_hours": 25,
        "used_hours": 18.5,
        "remaining_hours": 6.5,
        "overage_hours": 0,
        "percent_used": 74,
        "overage_rate": 50.00,
        "total_cost": 299.00,
        "overage_cost": 0.00,
        "recent_sessions": [
            {
                "id": str(uuid.uuid4()),
                "title": "Garage door automation troubleshooting",
                "duration_hours": 1.5,
                "date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "engineer": "Mike Johnson"
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Custom morning routine setup",
                "duration_hours": 2.0,
                "date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "engineer": "Sarah Chen"
            }
        ]
    }


@router.get("/family/support-hours/history")
async def get_support_hours_history(
    skip: int = 0,
    limit: int = 12,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get historical support hours usage by billing cycle"""
    # TODO: Query actual history from database
    return {
        "total": 6,
        "cycles": [
            {
                "period": "November 2024",
                "included": 25,
                "used": 18.5,
                "overage": 0,
                "cost": 299.00
            },
            {
                "period": "October 2024",
                "included": 25,
                "used": 28.0,
                "overage": 3.0,
                "cost": 449.00
            }
        ]
    }


# ============================================================================
# SUPPORT TICKET ENDPOINTS
# ============================================================================

@router.get("/family/support-tickets")
async def list_support_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List support tickets"""
    # TODO: Query actual tickets from database
    return {
        "total": 2,
        "tickets": [
            {
                "id": str(uuid.uuid4()),
                "ticket_number": "FAM-2025-001",
                "title": "Garage door automation not triggering",
                "description": "Automation for garage door opener stops working after sunset",
                "priority": "high",
                "status": "in_progress",
                "category": "automation",
                "assigned_to": "Mike Johnson",
                "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "updated_at": (datetime.utcnow() - timedelta(hours=5)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "ticket_number": "FAM-2025-002",
                "title": "Request: Custom morning routine",
                "description": "Need help creating a complex morning routine with multiple conditions",
                "priority": "medium",
                "status": "waiting_customer",
                "category": "automation",
                "assigned_to": "Sarah Chen",
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        ]
    }


@router.post("/family/support-tickets")
async def create_support_ticket(
    title: str,
    description: str,
    priority: TicketPriority = TicketPriority.MEDIUM,
    category: Optional[str] = None,
    device_id: Optional[uuid.UUID] = None,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new support ticket"""
    # TODO: Create actual ticket in database
    ticket_number = f"FAM-{datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"

    return {
        "id": str(uuid.uuid4()),
        "ticket_number": ticket_number,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "open",
        "category": category,
        "created_at": datetime.utcnow().isoformat(),
        "message": "Support ticket created successfully. Our team will respond within 4 hours."
    }


@router.get("/family/support-tickets/{ticket_id}")
async def get_support_ticket(
    ticket_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get support ticket details including comments"""
    # TODO: Query actual ticket from database
    return {
        "id": str(ticket_id),
        "ticket_number": "FAM-2025-001",
        "title": "Garage door automation not triggering",
        "description": "Automation for garage door opener stops working after sunset",
        "priority": "high",
        "status": "in_progress",
        "category": "automation",
        "assigned_to": "Mike Johnson",
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "comments": [
            {
                "id": str(uuid.uuid4()),
                "author": "Mike Johnson",
                "author_type": "engineer",
                "content": "I've reviewed the automation and found the issue. The sun sensor condition needs to be adjusted.",
                "created_at": (datetime.utcnow() - timedelta(hours=5)).isoformat()
            }
        ]
    }


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@router.get("/family/alerts")
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List alerts for family account"""
    # TODO: Query actual alerts from database
    return {
        "total": 5,
        "critical": 1,
        "warning": 2,
        "info": 2,
        "alerts": [
            {
                "id": str(uuid.uuid4()),
                "title": "Water Leak Detected",
                "message": "Water sensor in laundry room detected moisture",
                "severity": "critical",
                "status": "active",
                "source_type": "device",
                "source_name": "Laundry Room Sensor",
                "device_name": "Laundry Room Sensor",
                "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Front Door Lock Battery Low",
                "message": "Smart lock battery at 15% - replacement recommended",
                "severity": "warning",
                "status": "active",
                "source_type": "device",
                "source_name": "Front Door Lock",
                "device_name": "Front Door Lock",
                "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            }
        ]
    }


@router.post("/family/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert"""
    # TODO: Update alert status in database
    return {
        "id": str(alert_id),
        "status": "acknowledged",
        "acknowledged_at": datetime.utcnow().isoformat(),
        "acknowledged_by": auth_user.email
    }


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@router.get("/family/billing")
async def get_current_billing(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current month billing summary"""
    # TODO: Calculate actual billing from database
    return {
        "billing_period_start": (datetime.utcnow() - timedelta(days=18)).isoformat(),
        "billing_period_end": (datetime.utcnow() + timedelta(days=12)).isoformat(),
        "base_subscription": 299.00,
        "addons_total": 500.00,
        "support_hours_base": 0.00,
        "support_hours_overage": 0.00,
        "custom_services": 0.00,
        "subtotal": 799.00,
        "tax": 71.91,
        "total": 870.91,
        "status": "current",
        "line_items": [
            {"description": "Pro Plan Subscription", "amount": 299.00},
            {"description": "Extra 10 Support Hours", "amount": 450.00},
            {"description": "Priority Alert Monitoring", "amount": 50.00}
        ]
    }


@router.get("/family/billing/invoices")
async def list_invoices(
    skip: int = 0,
    limit: int = Query(default=12, le=100),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List billing invoices"""
    # TODO: Query actual invoices from database
    return {
        "total": 10,
        "invoices": [
            {
                "id": str(uuid.uuid4()),
                "invoice_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "due_date": (datetime.utcnow() + timedelta(days=25)).isoformat(),
                "total": 870.91,
                "status": "paid",
                "paid_at": (datetime.utcnow() - timedelta(days=4)).isoformat()
            }
        ]
    }


# ============================================================================
# AUTOMATION LIBRARY ENDPOINTS
# ============================================================================

@router.get("/family/automations/library")
async def list_automation_templates(
    category: Optional[str] = None,
    tier: Optional[SubscriptionTier] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Browse automation template library"""
    # TODO: Query actual templates from database
    return {
        "total": 42,
        "templates": [
            {
                "id": str(uuid.uuid4()),
                "name": "Good Morning Routine",
                "description": "Gradually turn on lights, adjust temperature, and start coffee maker",
                "category": "convenience",
                "tier_requirement": "starter",
                "is_premium": False,
                "setup_fee": 0.00,
                "icon": "sun",
                "popularity_score": 95
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Advanced Security Mode",
                "description": "Arm security system, lock all doors, enable motion detection with alerts",
                "category": "security",
                "tier_requirement": "pro",
                "is_premium": True,
                "setup_fee": 200.00,
                "icon": "shield",
                "popularity_score": 88
            }
        ]
    }


@router.post("/family/automations/request")
async def request_custom_automation(
    name: str,
    description: str,
    required_devices: List[str],
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Request a custom automation to be built"""
    # TODO: Create automation request (could be a special ticket type)
    return {
        "request_id": str(uuid.uuid4()),
        "message": "Custom automation request received. Our team will review and provide a quote within 24 hours.",
        "estimated_response_time": "24 hours"
    }


# ============================================================================
# HOME HUB STATUS
# ============================================================================

@router.get("/family/hub")
async def get_home_hub_status(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get home hub status and health"""
    # TODO: Query actual hub from property_edge_nodes
    return {
        "id": str(uuid.uuid4()),
        "hostname": "home-hub-001",
        "ip_address": "192.168.1.100",
        "tailscale_ip": "100.64.1.100",
        "status": "online",
        "last_heartbeat": (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
        "uptime_hours": 720,
        "devices": 42,
        "automations": 18,
        "ha_version": "2024.11.1",
        "firmware_version": "1.2.3",
        "last_sync": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
        "resource_usage": {
            "cpu_percent": 35,
            "memory_percent": 62,
            "disk_percent": 45
        }
    }


# ============================================================================
# NOC DASHBOARD (INTERNAL OPERATIONS CENTER)
# ============================================================================

@router.get("/family/noc-dashboard")
async def get_noc_dashboard(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated NOC (Network Operations Center) dashboard metrics.
    Internal multi-client operations console for MSP staff.

    Returns:
        - clients_by_plan: Distribution of clients across subscription tiers
        - support_hours_remaining_top10: Top 10 clients with lowest remaining hours
        - open_tickets_by_client: Open support ticket counts per client
        - critical_alerts: Active critical alerts across all clients (last 24h)
        - hub_health_matrix: Hub health status for all clients
    """
    from db.models import SupportTicket, Client, PropertyEdgeNode, Alert

    # TODO: Add support_hours_remaining_top10 when support hours tracking is implemented
    # For now, return empty/mock data for that section
    support_hours_remaining_top10 = []

    # Query real clients by plan
    clients_result = await db.execute(
        select(Client.tier, func.count(Client.id))
        .group_by(Client.tier)
    )
    clients_by_tier = clients_result.all()
    clients_by_plan = [
        {"plan": tier.replace("tier_", ""), "count": count}
        for tier, count in clients_by_tier
    ]

    # Get total client count
    total_clients_result = await db.execute(select(func.count(Client.id)))
    total_clients = total_clients_result.scalar() or 0

    # Query open tickets by client (real data)
    open_tickets_query = await db.execute(
        select(
            Client.id,
            Client.name,
            func.count(SupportTicket.id).label('open_count'),
            func.sum(
                func.cast(
                    (SupportTicket.severity.in_(['high', 'critical'])),
                    Integer
                )
            ).label('high_priority_count')
        )
        .join(SupportTicket, SupportTicket.client_id == Client.id, isouter=True)
        .where(or_(SupportTicket.status.in_(['open', 'in_progress']), SupportTicket.id == None))
        .group_by(Client.id, Client.name)
        .having(func.count(SupportTicket.id) > 0)
        .order_by(func.count(SupportTicket.id).desc())
    )
    open_tickets_by_client = [
        {
            "client": name,
            "client_id": str(client_id),
            "open": open_count,
            "high_priority": high_priority_count or 0,
            "sla_breach": 0  # TODO: Add SLA breach count
        }
        for client_id, name, open_count, high_priority_count in open_tickets_query.all()
    ]

    # Total open tickets
    total_open_tickets_result = await db.execute(
        select(func.count(SupportTicket.id))
        .where(SupportTicket.status.in_(['open', 'in_progress']))
    )
    total_open_tickets = total_open_tickets_result.scalar() or 0

    # Query critical alerts from last 24h (real data)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    critical_alerts_query = await db.execute(
        select(Alert, Client.name, Client.id, PropertyEdgeNode.hostname)
        .join(PropertyEdgeNode, Alert.hub_id == PropertyEdgeNode.id, isouter=True)
        .join(Client, Client.edge_node_id == PropertyEdgeNode.id, isouter=True)
        .where(
            and_(
                Alert.severity == 'critical',
                Alert.occurred_at >= twenty_four_hours_ago,
                Alert.status.in_(['open', 'acknowledged'])
            )
        )
        .order_by(Alert.occurred_at.desc())
        .limit(20)
    )
    critical_alerts = [
        {
            "id": str(alert.id),
            "client": client_name or "Unknown",
            "client_id": str(client_id) if client_id else None,
            "hub": hub_hostname or "Unknown",
            "message": alert.message,
            "severity": alert.severity,
            "category": alert.category,
            "timestamp": alert.occurred_at.isoformat(),
            "acknowledged": alert.status == 'acknowledged'
        }
        for alert, client_name, client_id, hub_hostname in critical_alerts_query.all()
    ]

    # Hub health matrix (real data)
    hub_health_query = await db.execute(
        select(
            Client.id,
            Client.name,
            func.count(PropertyEdgeNode.id).label('hubs_total'),
            func.sum(
                func.cast(
                    (PropertyEdgeNode.status == 'online'),
                    Integer
                )
            ).label('healthy'),
            func.sum(
                func.cast(
                    (PropertyEdgeNode.status.in_(['warning', 'error'])),
                    Integer
                )
            ).label('degraded'),
            func.sum(
                func.cast(
                    (PropertyEdgeNode.status == 'offline'),
                    Integer
                )
            ).label('offline')
        )
        .join(PropertyEdgeNode, Client.edge_node_id == PropertyEdgeNode.id, isouter=True)
        .group_by(Client.id, Client.name)
        .order_by(Client.name)
    )
    hub_health_matrix = [
        {
            "client": name,
            "client_id": str(client_id),
            "hubs_total": hubs_total or 0,
            "healthy": healthy or 0,
            "degraded": degraded or 0,
            "offline": offline or 0
        }
        for client_id, name, hubs_total, healthy, degraded, offline in hub_health_query.all()
    ]

    # Total hubs
    total_hubs_result = await db.execute(select(func.count(PropertyEdgeNode.id)))
    total_hubs = total_hubs_result.scalar() or 0

    return {
        "clients_by_plan": clients_by_plan,
        "support_hours_remaining_top10": support_hours_remaining_top10,  # TODO: Implement
        "open_tickets_by_client": open_tickets_by_client,
        "critical_alerts": critical_alerts,
        "hub_health_matrix": hub_health_matrix,
        "timestamp": datetime.utcnow().isoformat(),
        "total_clients": total_clients,
        "total_hubs": total_hubs,
        "total_open_tickets": total_open_tickets,
        "total_critical_alerts_24h": len(critical_alerts)
    }
