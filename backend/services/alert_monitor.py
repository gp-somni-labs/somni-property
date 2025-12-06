"""
Alert Monitor Service
Monitors critical alerts and auto-creates support tickets
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from db.models import Alert, SupportTicket, Client
from core.config import settings
from services.notification_service import send_notification, send_sla_breach_notification

logger = logging.getLogger(__name__)


def get_sla_hours(severity: str) -> int:
    """Get SLA hours based on severity"""
    sla_map = {
        'critical': settings.SLA_CRITICAL_HOURS,
        'high': settings.SLA_HIGH_HOURS,
        'medium': settings.SLA_MEDIUM_HOURS,
        'low': settings.SLA_LOW_HOURS,
    }
    return sla_map.get(severity.lower(), settings.SLA_MEDIUM_HOURS)


async def check_critical_alerts_and_create_tickets(db: AsyncSession):
    """
    Check for new critical alerts and auto-create support tickets.

    This function should be called periodically (e.g., every 5 minutes) as a background task.

    Logic:
    1. Query for new critical alerts (last 5 minutes)
    2. For each alert:
       - Check if ticket already exists for this alert (avoid duplicates)
       - Check if open ticket exists for same hub+category in last 4 hours (deduplication)
       - If neither exists, create ticket with appropriate SLA
    """
    try:
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

        # Get new critical alerts
        alerts_query = await db.execute(
            select(Alert).where(
                Alert.severity == 'critical',
                Alert.occurred_at >= five_minutes_ago,
                Alert.status == 'open'
            )
        )
        alerts = alerts_query.scalars().all()

        tickets_created = 0

        for alert in alerts:
            # Check for existing ticket for this alert
            existing_query = await db.execute(
                select(SupportTicket).where(
                    SupportTicket.alert_id == alert.id
                )
            )
            if existing_query.scalar():
                logger.debug(f"Ticket already exists for alert {alert.id}, skipping")
                continue

            # Check for recent ticket (deduplication - same hub + category in last 4 hours)
            four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
            recent_query = await db.execute(
                select(SupportTicket).where(
                    and_(
                        SupportTicket.hub_id == alert.hub_id,
                        SupportTicket.category == alert.category,
                        SupportTicket.status.in_(['open', 'in_progress']),
                        SupportTicket.created_at >= four_hours_ago
                    )
                )
            )
            if recent_query.scalar():
                logger.info(
                    f"Recent ticket exists for hub {alert.hub_id} + category {alert.category}, skipping"
                )
                continue

            # Get client_id from hub if available
            client_id = None
            if alert.hub_id:
                # Try to find client associated with this hub
                client_query = await db.execute(
                    select(Client).where(Client.edge_node_id == alert.hub_id)
                )
                client = client_query.scalar()
                if client:
                    client_id = client.id

            # Create ticket
            sla_hours = get_sla_hours('critical')
            ticket = SupportTicket(
                alert_id=alert.id,
                hub_id=alert.hub_id,
                client_id=client_id,
                category=alert.category,
                severity='critical',
                title=f"Critical Alert: {alert.message[:200]}",  # Truncate if too long
                description=alert.message,
                status='open',
                priority='critical',
                sla_due_at=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
            )
            db.add(ticket)
            tickets_created += 1

            logger.info(
                f"Auto-created support ticket for critical alert {alert.id}: {ticket.title}"
            )

            # Send notification for new critical ticket
            try:
                await send_notification(
                    title=f"🚨 Critical Ticket Created",
                    message=f"**Ticket:** {ticket.title}\n\n**Alert:** {alert.message[:200]}",
                    priority='high',
                    tags=['critical', 'ticket', 'auto-created']
                )
            except Exception as e:
                logger.error(f"Failed to send notification for ticket: {e}")

        await db.commit()

        if tickets_created > 0:
            logger.info(f"Alert monitor created {tickets_created} new support tickets")

        return tickets_created

    except Exception as e:
        logger.error(f"Error in alert monitor: {e}", exc_info=True)
        await db.rollback()
        raise


async def check_sla_breaches(db: AsyncSession):
    """
    Check for SLA breaches and mark tickets accordingly.

    This should be called periodically (e.g., every 15 minutes).
    """
    try:
        now = datetime.now(timezone.utc)

        # Find tickets that have breached SLA
        breached_query = await db.execute(
            select(SupportTicket).where(
                and_(
                    SupportTicket.status.in_(['open', 'in_progress']),
                    SupportTicket.sla_due_at <= now,
                    SupportTicket.sla_breach == False
                )
            )
        )
        breached_tickets = breached_query.scalars().all()

        for ticket in breached_tickets:
            ticket.sla_breach = True
            logger.warning(
                f"SLA breach detected for ticket {ticket.id}: {ticket.title}"
            )

            # Calculate hours overdue (ensure timezone-aware comparison)
            sla_due = ticket.sla_due_at
            if sla_due.tzinfo is None:
                sla_due = sla_due.replace(tzinfo=timezone.utc)
            hours_overdue = (now - sla_due).total_seconds() / 3600

            # Send SLA breach notification
            try:
                await send_sla_breach_notification(
                    ticket_id=str(ticket.id),
                    ticket_title=ticket.title,
                    severity=ticket.severity or 'medium',
                    hours_overdue=hours_overdue
                )
            except Exception as e:
                logger.error(f"Failed to send SLA breach notification: {e}")

        await db.commit()

        if breached_tickets:
            logger.info(f"Marked {len(breached_tickets)} tickets as SLA breached")

        return len(breached_tickets)

    except Exception as e:
        logger.error(f"Error checking SLA breaches: {e}", exc_info=True)
        await db.rollback()
        raise
