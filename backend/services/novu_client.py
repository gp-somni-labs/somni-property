"""
Novu Integration Client for SomniProperty

Integrates with self-hosted Novu (unified notification infrastructure) for:
- Multi-channel notifications (email, SMS, in-app, push)
- Workflow-based notification management
- Template management
- Subscriber management
- Notification preferences
- Delivery tracking

Replaces simple Gotify/NTFY with enterprise-grade notification workflows.

Novu Service: novu-api.novu.svc.cluster.local:3000
Documentation: https://docs.novu.co
API Docs: https://docs.novu.co/api/overview
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Novu notification channel types"""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    CHAT = "chat"


class NotificationStatus(Enum):
    """Novu notification status"""
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    ERROR = "error"


class Subscriber(BaseModel):
    """Novu subscriber (notification recipient)"""
    subscriber_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    data: Optional[Dict[str, Any]] = {}


class NotificationTemplate(BaseModel):
    """Novu notification template/workflow"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    active: bool = True
    draft: bool = False
    critical: bool = False
    tags: Optional[List[str]] = []
    steps: Optional[List[Dict[str, Any]]] = []


class TriggerEvent(BaseModel):
    """Novu trigger event payload"""
    name: str  # Template identifier
    to: Dict[str, Any]  # Subscriber info or subscriber_id
    payload: Dict[str, Any]  # Template variables
    overrides: Optional[Dict[str, Any]] = {}


class NovuClient:
    """Client for interacting with Novu API"""

    def __init__(
        self,
        base_url: str = "http://novu-api.novu.svc.cluster.local:3000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Novu client

        Args:
            base_url: Novu API service URL
            api_key: Novu API key (from Settings → API Keys)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        return headers

    # ========================================
    # Subscriber Management
    # ========================================

    async def create_subscriber(
        self,
        subscriber_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Subscriber]:
        """
        Create or update a subscriber

        Use for:
        - Property managers (receive approval requests)
        - Tenants (receive payment reminders, work order updates)
        - Contractors (receive work order assignments)

        Args:
            subscriber_id: Unique subscriber ID (e.g., "manager-{user_id}", "tenant-{tenant_id}")
            email: Subscriber email
            phone: Subscriber phone (for SMS)
            first_name: First name
            last_name: Last name
            data: Additional metadata (e.g., {"role": "manager", "property_id": "..."})

        Returns:
            Created/updated subscriber or None on failure
        """
        try:
            payload = {
                "subscriberId": subscriber_id,
                "email": email,
                "phone": phone,
                "firstName": first_name,
                "lastName": last_name,
                "data": data or {}
            }

            response = await self.client.post(
                f"{self.base_url}/v1/subscribers",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data_resp = response.json()
                sub = data_resp.get("data", data_resp)
                return Subscriber(
                    subscriber_id=sub.get("subscriberId"),
                    email=sub.get("email"),
                    phone=sub.get("phone"),
                    first_name=sub.get("firstName"),
                    last_name=sub.get("lastName"),
                    data=sub.get("data", {})
                )
            else:
                logger.error(f"Failed to create subscriber: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating subscriber: {e}")
            return None

    async def get_subscriber(self, subscriber_id: str) -> Optional[Subscriber]:
        """Get subscriber by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/subscribers/{subscriber_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                sub = data.get("data", data)
                return Subscriber(
                    subscriber_id=sub.get("subscriberId"),
                    email=sub.get("email"),
                    phone=sub.get("phone"),
                    first_name=sub.get("firstName"),
                    last_name=sub.get("lastName"),
                    data=sub.get("data", {})
                )
            return None

        except Exception as e:
            logger.error(f"Error getting subscriber: {e}")
            return None

    async def update_subscriber_preferences(
        self,
        subscriber_id: str,
        template_id: str,
        channel: ChannelType,
        enabled: bool
    ) -> bool:
        """
        Update subscriber notification preferences

        Allow users to opt-in/opt-out of specific notification types

        Args:
            subscriber_id: Subscriber ID
            template_id: Notification template ID
            channel: Channel type (email, SMS, etc.)
            enabled: Enable or disable notifications

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "channel": {
                    "type": channel.value,
                    "enabled": enabled
                }
            }

            response = await self.client.patch(
                f"{self.base_url}/v1/subscribers/{subscriber_id}/preferences/{template_id}",
                headers=self._headers(),
                json=payload
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error updating subscriber preferences: {e}")
            return False

    # ========================================
    # Trigger Notifications
    # ========================================

    async def trigger(
        self,
        event_name: str,
        subscriber_id: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, str]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Trigger a notification workflow

        Use for:
        - Approval requests: "approval-required"
        - Work order updates: "work-order-status-changed"
        - Payment reminders: "payment-due"
        - Emergency notifications: "emergency-alert"

        Args:
            event_name: Template/workflow identifier
            subscriber_id: Subscriber ID to notify
            payload: Template variables (e.g., {"work_order_id": "WO-123", "unit": "204"})
            actor: Who triggered the notification (e.g., {"subscriberId": "system"})
            overrides: Channel-specific overrides

        Returns:
            Transaction ID or None on failure
        """
        try:
            request_payload = {
                "name": event_name,
                "to": {
                    "subscriberId": subscriber_id
                },
                "payload": payload
            }

            if actor:
                request_payload["actor"] = actor
            if overrides:
                request_payload["overrides"] = overrides

            response = await self.client.post(
                f"{self.base_url}/v1/events/trigger",
                headers=self._headers(),
                json=request_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                result = data.get("data", data)
                return result.get("transactionId")
            else:
                logger.error(f"Failed to trigger notification: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error triggering notification: {e}")
            return None

    async def trigger_broadcast(
        self,
        event_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Trigger a broadcast notification to all subscribers

        Use for:
        - System-wide announcements
        - Emergency alerts
        - Maintenance schedules

        Args:
            event_name: Template/workflow identifier
            payload: Template variables
            actor: Who triggered the notification

        Returns:
            Transaction ID or None on failure
        """
        try:
            request_payload = {
                "name": event_name,
                "payload": payload
            }

            if actor:
                request_payload["actor"] = actor

            response = await self.client.post(
                f"{self.base_url}/v1/events/trigger/broadcast",
                headers=self._headers(),
                json=request_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                result = data.get("data", data)
                return result.get("transactionId")
            else:
                logger.error(f"Failed to trigger broadcast: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error triggering broadcast: {e}")
            return None

    # ========================================
    # Template/Workflow Management
    # ========================================

    async def create_notification_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        critical: bool = False
    ) -> Optional[NotificationTemplate]:
        """
        Create a notification workflow

        Steps define the notification flow across channels:
        [
            {
                "type": "email",
                "name": "Email Notification",
                "subject": "Approval Required: {{work_order_title}}",
                "content": "..."
            },
            {
                "type": "sms",
                "name": "SMS Alert",
                "content": "Work order {{work_order_id}} needs approval"
            }
        ]

        Args:
            name: Workflow identifier (e.g., "approval-required")
            description: Workflow description
            steps: List of notification steps
            tags: Tags for organization
            critical: Mark as critical (bypasses preferences)

        Returns:
            Created workflow or None on failure
        """
        try:
            payload = {
                "name": name,
                "description": description,
                "steps": steps,
                "tags": tags or [],
                "critical": critical,
                "active": True
            }

            response = await self.client.post(
                f"{self.base_url}/v1/notification-templates",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                template = data.get("data", data)
                return NotificationTemplate(
                    id=template.get("_id"),
                    name=template.get("name"),
                    description=template.get("description"),
                    active=template.get("active", True),
                    critical=template.get("critical", False),
                    tags=template.get("tags", [])
                )
            else:
                logger.error(f"Failed to create workflow: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            return None

    async def list_workflows(self) -> List[NotificationTemplate]:
        """List all notification workflows"""
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/notification-templates",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                templates = data.get("data", [])
                return [
                    NotificationTemplate(
                        id=template.get("_id"),
                        name=template.get("name"),
                        description=template.get("description"),
                        active=template.get("active", True),
                        critical=template.get("critical", False),
                        tags=template.get("tags", [])
                    )
                    for template in templates
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return []

    # ========================================
    # Notification History & Tracking
    # ========================================

    async def get_notifications(
        self,
        subscriber_id: str,
        page: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get notification history for a subscriber

        Args:
            subscriber_id: Subscriber ID
            page: Page number (0-indexed)
            limit: Results per page

        Returns:
            List of notifications
        """
        try:
            params = {
                "page": page,
                "limit": limit
            }

            response = await self.client.get(
                f"{self.base_url}/v1/subscribers/{subscriber_id}/notifications",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []

        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []

    async def mark_notification_as_read(
        self,
        subscriber_id: str,
        notification_id: str
    ) -> bool:
        """
        Mark notification as read

        Args:
            subscriber_id: Subscriber ID
            notification_id: Notification ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/subscribers/{subscriber_id}/messages/{notification_id}/read",
                headers=self._headers()
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def send_approval_request(
        self,
        manager_id: str,
        action_type: str,
        action_title: str,
        action_description: str,
        estimated_cost: Optional[float] = None,
        urgency: str = "normal",
        approval_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Send approval request notification to property manager

        Triggers multi-channel notification:
        - Email with approval/reject buttons
        - SMS for urgent requests
        - In-app notification
        - Push notification (if mobile app configured)

        Args:
            manager_id: Property manager subscriber ID
            action_type: Type of action (e.g., "create_work_order")
            action_title: Action title
            action_description: Action description
            estimated_cost: Estimated cost
            urgency: Urgency level (low, normal, high, urgent)
            approval_url: URL to approval page
            metadata: Additional metadata

        Returns:
            Transaction ID or None on failure
        """
        payload = {
            "action_type": action_type,
            "action_title": action_title,
            "action_description": action_description,
            "estimated_cost": estimated_cost,
            "urgency": urgency,
            "approval_url": approval_url or "",
            "metadata": metadata or {}
        }

        # Use different templates based on urgency
        event_name = "approval-required"
        if urgency in ["urgent", "high"]:
            event_name = "approval-required-urgent"

        return await self.trigger(
            event_name=event_name,
            subscriber_id=manager_id,
            payload=payload
        )

    async def send_work_order_update(
        self,
        tenant_id: str,
        work_order_id: str,
        work_order_title: str,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Send work order status update to tenant

        Args:
            tenant_id: Tenant subscriber ID
            work_order_id: Work order ID
            work_order_title: Work order title
            status: New status
            message: Update message
            metadata: Additional metadata

        Returns:
            Transaction ID or None on failure
        """
        payload = {
            "work_order_id": work_order_id,
            "work_order_title": work_order_title,
            "status": status,
            "message": message,
            "metadata": metadata or {}
        }

        return await self.trigger(
            event_name="work-order-update",
            subscriber_id=tenant_id,
            payload=payload
        )

    async def send_payment_reminder(
        self,
        tenant_id: str,
        amount: float,
        due_date: datetime,
        payment_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Send payment reminder to tenant

        Args:
            tenant_id: Tenant subscriber ID
            amount: Amount due
            due_date: Payment due date
            payment_url: URL to payment page
            metadata: Additional metadata

        Returns:
            Transaction ID or None on failure
        """
        payload = {
            "amount": amount,
            "due_date": due_date.isoformat(),
            "payment_url": payment_url or "",
            "metadata": metadata or {}
        }

        return await self.trigger(
            event_name="payment-reminder",
            subscriber_id=tenant_id,
            payload=payload
        )


# ========================================
# Singleton instance management
# ========================================

_novu_client: Optional[NovuClient] = None


def get_novu_client(
    base_url: str = "http://novu-api.novu.svc.cluster.local:3000",
    api_key: Optional[str] = None
) -> NovuClient:
    """Get singleton Novu client instance"""
    global _novu_client
    if _novu_client is None:
        _novu_client = NovuClient(base_url=base_url, api_key=api_key)
    return _novu_client


async def close_novu_client():
    """Close singleton Novu client"""
    global _novu_client
    if _novu_client:
        await _novu_client.close()
        _novu_client = None
