"""
Notification Service - Send notifications via Gotify and NTFY (self-hosted)
For internal property manager notifications about pending approvals
"""

import logging
from typing import Dict, List, Optional, Any
import httpx
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    MIN = 1      # No sound, low priority
    LOW = 2      # No sound
    DEFAULT = 3  # Normal sound
    HIGH = 4     # High priority sound
    URGENT = 5   # Urgent sound and notification


class NotificationService:
    """
    Unified notification service using self-hosted Gotify and NTFY
    """

    def __init__(
        self,
        gotify_url: str = "http://gotify.monitoring.svc.cluster.local",
        ntfy_url: str = "http://ntfy.monitoring.svc.cluster.local",
        gotify_token: Optional[str] = None,
        ntfy_token: Optional[str] = None
    ):
        self.gotify_url = gotify_url
        self.ntfy_url = ntfy_url
        self.gotify_token = gotify_token
        self.ntfy_token = ntfy_token
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_approval_request(
        self,
        title: str,
        message: str,
        action_id: str,
        urgency: str = 'normal',
        estimated_cost: Optional[float] = None,
        requester_name: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, bool]:
        """
        Send approval request notification to property managers
        Returns dict with success status for each channel
        """
        # Determine priority based on urgency
        priority = self._urgency_to_priority(urgency)

        # Build rich notification content
        full_message = self._build_approval_message(
            message=message,
            action_id=action_id,
            estimated_cost=estimated_cost,
            requester_name=requester_name,
            action_url=action_url
        )

        results = {}

        # Send via Gotify
        try:
            gotify_success = await self.send_gotify(
                title=title,
                message=full_message,
                priority=priority.value,
                extras={
                    'client::display': {
                        'contentType': 'text/markdown'
                    },
                    'action_id': action_id,
                    'action_type': 'approval_request',
                    'urgency': urgency,
                    'estimated_cost': estimated_cost,
                    **(metadata or {})
                }
            )
            results['gotify'] = gotify_success
        except Exception as e:
            logger.error(f"Gotify notification error: {e}")
            results['gotify'] = False

        # Send via NTFY
        try:
            ntfy_success = await self.send_ntfy(
                topic='somniproperty-approvals',
                title=title,
                message=full_message,
                priority=priority.value,
                tags=['approval', urgency],
                click_url=action_url,
                actions=[
                    {
                        'action': 'view',
                        'label': 'View Details',
                        'url': action_url
                    },
                    {
                        'action': 'http',
                        'label': 'Approve',
                        'url': f'{action_url}/approve',
                        'method': 'POST'
                    },
                    {
                        'action': 'http',
                        'label': 'Reject',
                        'url': f'{action_url}/reject',
                        'method': 'POST',
                        'clear': True
                    }
                ] if action_url else None
            )
            results['ntfy'] = ntfy_success
        except Exception as e:
            logger.error(f"NTFY notification error: {e}")
            results['ntfy'] = False

        return results

    async def send_gotify(
        self,
        title: str,
        message: str,
        priority: int = 3,
        extras: Optional[Dict] = None
    ) -> bool:
        """Send notification via Gotify"""
        if not self.gotify_token:
            logger.warning("Gotify token not configured, skipping")
            return False

        try:
            url = f"{self.gotify_url}/message?token={self.gotify_token}"

            data = {
                'title': title,
                'message': message,
                'priority': priority
            }

            if extras:
                data['extras'] = extras

            response = await self.client.post(url, json=data)
            response.raise_for_status()

            logger.info(f"Gotify notification sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Gotify send error: {e}")
            return False

    async def send_ntfy(
        self,
        topic: str,
        title: str,
        message: str,
        priority: int = 3,
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
        actions: Optional[List[Dict]] = None,
        attach_url: Optional[str] = None
    ) -> bool:
        """Send notification via NTFY"""
        try:
            url = f"{self.ntfy_url}/{topic}"

            headers = {
                'Title': title,
                'Priority': str(priority),
                'Tags': ','.join(tags) if tags else ''
            }

            if self.ntfy_token:
                headers['Authorization'] = f'Bearer {self.ntfy_token}'

            if click_url:
                headers['Click'] = click_url

            if attach_url:
                headers['Attach'] = attach_url

            if actions:
                headers['Actions'] = '; '.join([
                    ', '.join([f'{k}={v}' for k, v in action.items()])
                    for action in actions
                ])

            response = await self.client.post(
                url,
                content=message,
                headers=headers
            )
            response.raise_for_status()

            logger.info(f"NTFY notification sent to {topic}: {title}")
            return True

        except Exception as e:
            logger.error(f"NTFY send error: {e}")
            return False

    async def send_approval_decision(
        self,
        action_id: str,
        decision: str,  # 'approved' or 'rejected'
        requester_contact: str,  # Email or phone
        action_title: str,
        decision_reason: Optional[str] = None,
        channel: str = 'email'  # 'email' or 'sms'
    ) -> bool:
        """
        Send approval decision notification to requester (tenant/contractor)
        This uses email/SMS, not Gotify/NTFY
        """
        # This is handled by email_service.py and sms_service.py
        # Just log here for tracking
        logger.info(
            f"Approval decision notification: {decision} for action {action_id} "
            f"to {requester_contact} via {channel}"
        )
        return True

    async def send_reminder(
        self,
        action_id: str,
        title: str,
        hours_pending: int,
        urgency: str = 'normal'
    ) -> Dict[str, bool]:
        """Send reminder for pending approval"""
        priority = self._urgency_to_priority(urgency)

        message = f"""
⏰ **Approval Reminder**

This action has been pending for **{hours_pending} hours**.

Action ID: `{action_id}`

Please review and approve/reject this request.
"""

        results = {}

        try:
            results['gotify'] = await self.send_gotify(
                title=f"⏰ REMINDER: {title}",
                message=message,
                priority=min(priority.value + 1, 10)  # Increase priority for reminders
            )
        except Exception as e:
            logger.error(f"Reminder Gotify error: {e}")
            results['gotify'] = False

        try:
            results['ntfy'] = await self.send_ntfy(
                topic='somniproperty-approvals',
                title=f"⏰ REMINDER: {title}",
                message=message,
                priority=min(priority.value + 1, 5),
                tags=['reminder', 'approval']
            )
        except Exception as e:
            logger.error(f"Reminder NTFY error: {e}")
            results['ntfy'] = False

        return results

    async def send_execution_result(
        self,
        action_id: str,
        action_title: str,
        success: bool,
        result_message: str
    ) -> Dict[str, bool]:
        """Notify about action execution result"""
        emoji = "✅" if success else "❌"
        title = f"{emoji} Action Executed: {action_title}"

        message = f"""
**Action ID:** `{action_id}`
**Status:** {'Success' if success else 'Failed'}

{result_message}
"""

        results = {}

        try:
            results['gotify'] = await self.send_gotify(
                title=title,
                message=message,
                priority=4 if not success else 3
            )
        except Exception as e:
            results['gotify'] = False

        try:
            results['ntfy'] = await self.send_ntfy(
                topic='somniproperty-approvals',
                title=title,
                message=message,
                priority=4 if not success else 3,
                tags=['execution', 'success' if success else 'error']
            )
        except Exception as e:
            results['ntfy'] = False

        return results

    def _urgency_to_priority(self, urgency: str) -> NotificationPriority:
        """Convert urgency string to notification priority"""
        mapping = {
            'low': NotificationPriority.LOW,
            'normal': NotificationPriority.DEFAULT,
            'high': NotificationPriority.HIGH,
            'critical': NotificationPriority.URGENT,
            'emergency': NotificationPriority.URGENT
        }
        return mapping.get(urgency, NotificationPriority.DEFAULT)

    def _build_approval_message(
        self,
        message: str,
        action_id: str,
        estimated_cost: Optional[float] = None,
        requester_name: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> str:
        """Build rich markdown message for approval notification"""
        parts = []

        if requester_name:
            parts.append(f"**Requester:** {requester_name}")

        parts.append(f"\n{message}\n")

        if estimated_cost is not None:
            parts.append(f"**Estimated Cost:** ${estimated_cost:.2f}")

        parts.append(f"\n**Action ID:** `{action_id}`")

        if action_url:
            parts.append(f"\n[View Details & Approve/Reject]({action_url})")

        return '\n'.join(parts)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance (will be configured with tokens from environment)
notification_service = None


def get_notification_service(
    gotify_token: Optional[str] = None,
    ntfy_token: Optional[str] = None
) -> NotificationService:
    """Get or create notification service singleton"""
    global notification_service
    if notification_service is None:
        notification_service = NotificationService(
            gotify_token=gotify_token,
            ntfy_token=ntfy_token
        )
    return notification_service


async def send_notification(
    title: str,
    message: str,
    priority: str = 'default',
    topic: str = 'somniproperty-alerts',
    tags: Optional[List[str]] = None,
    action_url: Optional[str] = None
) -> Dict[str, bool]:
    """
    Convenience function for sending notifications via both Gotify and NTFY.

    Args:
        title: Notification title
        message: Notification message (supports markdown)
        priority: Priority level ('min', 'low', 'default', 'high', 'urgent')
        topic: NTFY topic (default: somniproperty-alerts)
        tags: Optional list of tags for NTFY
        action_url: Optional URL to open on click

    Returns:
        Dict with success status for each channel
    """
    service = get_notification_service()

    # Map priority string to enum
    priority_map = {
        'min': NotificationPriority.MIN,
        'low': NotificationPriority.LOW,
        'default': NotificationPriority.DEFAULT,
        'high': NotificationPriority.HIGH,
        'urgent': NotificationPriority.URGENT,
        'critical': NotificationPriority.URGENT,
    }
    priority_level = priority_map.get(priority.lower(), NotificationPriority.DEFAULT)

    results = {}

    # Send via Gotify
    try:
        results['gotify'] = await service.send_gotify(
            title=title,
            message=message,
            priority=priority_level.value,
            extras={
                'client::display': {'contentType': 'text/markdown'}
            }
        )
    except Exception as e:
        logger.error(f"Gotify notification error: {e}")
        results['gotify'] = False

    # Send via NTFY
    try:
        results['ntfy'] = await service.send_ntfy(
            topic=topic,
            title=title,
            message=message,
            priority=priority_level.value,
            tags=tags or [],
            click_url=action_url
        )
    except Exception as e:
        logger.error(f"NTFY notification error: {e}")
        results['ntfy'] = False

    return results


async def send_critical_alert_notification(
    alert_type: str,
    message: str,
    source: str,
    action_url: Optional[str] = None
) -> Dict[str, bool]:
    """
    Send notification for critical IoT alerts (water leak, smoke, etc.)

    Args:
        alert_type: Type of alert (water_leak, smoke, co, unauthorized_access)
        message: Alert message
        source: Source device/sensor
        action_url: Optional URL to view alert details
    """
    emoji_map = {
        'water_leak': '💧',
        'smoke': '🔥',
        'co': '☠️',
        'fire': '🔥',
        'unauthorized_access': '🚨',
        'intrusion': '🚨',
        'temperature': '🌡️',
        'hvac_failure': '❄️',
    }

    emoji = emoji_map.get(alert_type.lower(), '⚠️')
    title = f"{emoji} CRITICAL: {alert_type.replace('_', ' ').title()}"

    full_message = f"""
**Source:** {source}

{message}

---
*This is an automated alert from SomniProperty IoT monitoring.*
"""

    return await send_notification(
        title=title,
        message=full_message,
        priority='urgent',
        topic='somniproperty-alerts',
        tags=['critical', alert_type.lower(), 'alert'],
        action_url=action_url
    )


async def send_sla_breach_notification(
    ticket_id: str,
    ticket_title: str,
    severity: str,
    hours_overdue: float,
    action_url: Optional[str] = None
) -> Dict[str, bool]:
    """
    Send notification for SLA breach on support ticket.

    Args:
        ticket_id: Ticket ID
        ticket_title: Ticket title
        severity: Ticket severity
        hours_overdue: Hours past SLA deadline
        action_url: Optional URL to view ticket
    """
    title = f"⏰ SLA BREACH: {ticket_title[:50]}"

    message = f"""
**Ticket ID:** `{ticket_id}`
**Severity:** {severity.upper()}
**Overdue:** {hours_overdue:.1f} hours

This ticket has exceeded its SLA deadline. Immediate attention required.
"""

    return await send_notification(
        title=title,
        message=message,
        priority='high',
        topic='somniproperty-alerts',
        tags=['sla', 'breach', severity.lower()],
        action_url=action_url
    )
