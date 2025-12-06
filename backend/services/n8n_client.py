"""
n8n Integration Client for SomniProperty

Integrates with self-hosted n8n (advanced workflow automation) for:
- Complex multi-step automation workflows
- Integration with external services (Stripe, Twilio, etc.)
- Scheduled automation tasks
- Event-driven workflows
- Data transformation and enrichment
- Custom business logic automation

n8n Service: n8n.ai.svc.cluster.local:5678
Documentation: https://docs.n8n.io
API Docs: https://docs.n8n.io/api/
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """n8n workflow status"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class ExecutionStatus(Enum):
    """n8n execution status"""
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WAITING = "waiting"
    CANCELED = "canceled"


class N8nWorkflow(BaseModel):
    """n8n workflow model"""
    id: Optional[str] = None
    name: str
    active: bool = False
    nodes: Optional[List[Dict[str, Any]]] = []
    connections: Optional[Dict[str, Any]] = {}
    settings: Optional[Dict[str, Any]] = {}
    static_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class N8nExecution(BaseModel):
    """n8n workflow execution model"""
    id: Optional[str] = None
    workflow_id: str
    finished: bool
    mode: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    status: str
    data: Optional[Dict[str, Any]] = None


class N8nWebhook(BaseModel):
    """n8n webhook configuration"""
    workflow_id: str
    webhook_id: str
    http_method: str = "POST"
    path: str
    response_mode: str = "onReceived"


class N8nClient:
    """Client for interacting with n8n API"""

    def __init__(
        self,
        base_url: str = "http://n8n.ai.svc.cluster.local:5678",
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize n8n client

        Args:
            base_url: n8n service URL
            api_key: n8n API key (from Settings → API)
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
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    # ========================================
    # Workflow Management
    # ========================================

    async def create_workflow(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        connections: Dict[str, Any],
        active: bool = False,
        settings: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[N8nWorkflow]:
        """
        Create a workflow in n8n

        Use for:
        - Payment processing automation
        - Tenant communication workflows
        - Maintenance scheduling
        - Integration with external services
        - Custom business logic

        Args:
            name: Workflow name
            nodes: List of workflow nodes (steps)
            connections: Node connections defining flow
            active: Activate workflow immediately
            settings: Workflow settings (timezone, error handling, etc.)
            tags: Tags for organization

        Returns:
            Created workflow or None on failure
        """
        try:
            payload = {
                "name": name,
                "nodes": nodes,
                "connections": connections,
                "active": active,
                "settings": settings or {},
                "tags": tags or []
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/workflows",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return N8nWorkflow(
                    id=data.get("id"),
                    name=data.get("name"),
                    active=data.get("active", False),
                    nodes=data.get("nodes", []),
                    connections=data.get("connections", {}),
                    settings=data.get("settings", {}),
                    static_data=data.get("staticData"),
                    tags=data.get("tags", []),
                    created_at=datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00")) if data.get("createdAt") else None,
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")) if data.get("updatedAt") else None
                )
            else:
                logger.error(f"Failed to create workflow: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            return None

    async def get_workflow(self, workflow_id: str) -> Optional[N8nWorkflow]:
        """Get workflow by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return N8nWorkflow(
                    id=data.get("id"),
                    name=data.get("name"),
                    active=data.get("active", False),
                    nodes=data.get("nodes", []),
                    connections=data.get("connections", {}),
                    settings=data.get("settings", {}),
                    static_data=data.get("staticData"),
                    tags=data.get("tags", []),
                    created_at=datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00")) if data.get("createdAt") else None,
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")) if data.get("updatedAt") else None
                )
            return None

        except Exception as e:
            logger.error(f"Error getting workflow: {e}")
            return None

    async def list_workflows(
        self,
        active: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> List[N8nWorkflow]:
        """
        List all workflows

        Args:
            active: Filter by active status
            tags: Filter by tags

        Returns:
            List of workflows
        """
        try:
            params = {}
            if active is not None:
                params["active"] = str(active).lower()
            if tags:
                params["tags"] = ",".join(tags)

            response = await self.client.get(
                f"{self.base_url}/api/v1/workflows",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                workflows = data.get("data", data)  # Handle both formats
                return [
                    N8nWorkflow(
                        id=workflow.get("id"),
                        name=workflow.get("name"),
                        active=workflow.get("active", False),
                        nodes=workflow.get("nodes", []),
                        connections=workflow.get("connections", {}),
                        settings=workflow.get("settings", {}),
                        tags=workflow.get("tags", []),
                        created_at=datetime.fromisoformat(workflow.get("createdAt").replace("Z", "+00:00")) if workflow.get("createdAt") else None,
                        updated_at=datetime.fromisoformat(workflow.get("updatedAt").replace("Z", "+00:00")) if workflow.get("updatedAt") else None
                    )
                    for workflow in workflows
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return []

    async def update_workflow(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        active: Optional[bool] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Optional[N8nWorkflow]:
        """
        Update a workflow

        Args:
            workflow_id: Workflow ID
            name: New workflow name
            active: Activate/deactivate workflow
            nodes: Updated nodes
            connections: Updated connections
            settings: Updated settings

        Returns:
            Updated workflow or None on failure
        """
        try:
            # Get existing workflow first
            existing = await self.get_workflow(workflow_id)
            if not existing:
                return None

            # Build update payload
            payload = {
                "name": name or existing.name,
                "nodes": nodes or existing.nodes,
                "connections": connections or existing.connections,
                "settings": settings or existing.settings
            }

            if active is not None:
                payload["active"] = active

            response = await self.client.patch(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                return N8nWorkflow(
                    id=data.get("id"),
                    name=data.get("name"),
                    active=data.get("active", False),
                    nodes=data.get("nodes", []),
                    connections=data.get("connections", {}),
                    settings=data.get("settings", {}),
                    tags=data.get("tags", []),
                    created_at=datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00")) if data.get("createdAt") else None,
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")) if data.get("updatedAt") else None
                )
            else:
                logger.error(f"Failed to update workflow: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error updating workflow: {e}")
            return None

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers()
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            return False

    async def activate_workflow(self, workflow_id: str) -> bool:
        """
        Activate a workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update_workflow(workflow_id, active=True)
        return result is not None

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        Deactivate a workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update_workflow(workflow_id, active=False)
        return result is not None

    # ========================================
    # Workflow Execution
    # ========================================

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[N8nExecution]:
        """
        Execute a workflow manually

        Args:
            workflow_id: Workflow ID
            data: Input data for workflow

        Returns:
            Execution result or None on failure
        """
        try:
            payload = {
                "workflowId": workflow_id
            }
            if data:
                payload["data"] = data

            response = await self.client.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return N8nExecution(
                    id=result.get("id"),
                    workflow_id=workflow_id,
                    finished=result.get("finished", False),
                    mode=result.get("mode", "manual"),
                    started_at=datetime.fromisoformat(result.get("startedAt").replace("Z", "+00:00")) if result.get("startedAt") else datetime.now(),
                    stopped_at=datetime.fromisoformat(result.get("stoppedAt").replace("Z", "+00:00")) if result.get("stoppedAt") else None,
                    status=result.get("status", "running"),
                    data=result.get("data")
                )
            else:
                logger.error(f"Failed to execute workflow: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return None

    async def get_execution(self, execution_id: str) -> Optional[N8nExecution]:
        """
        Get execution details by ID

        Args:
            execution_id: Execution ID

        Returns:
            Execution details or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/executions/{execution_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return N8nExecution(
                    id=data.get("id"),
                    workflow_id=data.get("workflowId"),
                    finished=data.get("finished", False),
                    mode=data.get("mode", "manual"),
                    started_at=datetime.fromisoformat(data.get("startedAt").replace("Z", "+00:00")) if data.get("startedAt") else datetime.now(),
                    stopped_at=datetime.fromisoformat(data.get("stoppedAt").replace("Z", "+00:00")) if data.get("stoppedAt") else None,
                    status=data.get("status", "running"),
                    data=data.get("data")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting execution: {e}")
            return None

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 20
    ) -> List[N8nExecution]:
        """
        List workflow executions

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by execution status
            limit: Maximum results

        Returns:
            List of executions
        """
        try:
            params = {"limit": limit}
            if workflow_id:
                params["workflowId"] = workflow_id
            if status:
                params["status"] = status.value

            response = await self.client.get(
                f"{self.base_url}/api/v1/executions",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                executions = data.get("data", data)
                return [
                    N8nExecution(
                        id=execution.get("id"),
                        workflow_id=execution.get("workflowId"),
                        finished=execution.get("finished", False),
                        mode=execution.get("mode", "manual"),
                        started_at=datetime.fromisoformat(execution.get("startedAt").replace("Z", "+00:00")) if execution.get("startedAt") else datetime.now(),
                        stopped_at=datetime.fromisoformat(execution.get("stoppedAt").replace("Z", "+00:00")) if execution.get("stoppedAt") else None,
                        status=execution.get("status", "running"),
                        data=execution.get("data")
                    )
                    for execution in executions
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing executions: {e}")
            return []

    # ========================================
    # Webhook Management
    # ========================================

    async def trigger_webhook(
        self,
        webhook_path: str,
        data: Dict[str, Any],
        query_params: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger a webhook workflow

        Use for:
        - Payment notifications from Stripe
        - SMS responses from Twilio
        - Calendar events from Cal.com
        - External service callbacks

        Args:
            webhook_path: Webhook path (e.g., "payment-received")
            data: Webhook payload
            query_params: Optional query parameters

        Returns:
            Webhook response or None on failure
        """
        try:
            url = f"{self.base_url}/webhook/{webhook_path}"

            response = await self.client.post(
                url,
                json=data,
                params=query_params
            )

            if response.status_code in [200, 201]:
                # Try to parse JSON response, fallback to text
                try:
                    return response.json()
                except Exception:
                    return {"response": response.text}
            else:
                logger.error(f"Failed to trigger webhook: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error triggering webhook: {e}")
            return None

    async def trigger_webhook_test(
        self,
        workflow_id: str,
        webhook_path: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Test a webhook workflow

        Args:
            workflow_id: Workflow ID
            webhook_path: Webhook path
            data: Test data

        Returns:
            Test response or None on failure
        """
        try:
            url = f"{self.base_url}/webhook-test/{webhook_path}"

            response = await self.client.post(
                url,
                json=data,
                params={"workflowId": workflow_id}
            )

            if response.status_code in [200, 201]:
                try:
                    return response.json()
                except Exception:
                    return {"response": response.text}
            else:
                logger.error(f"Failed to test webhook: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error testing webhook: {e}")
            return None

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def trigger_payment_workflow(
        self,
        tenant_id: str,
        amount: float,
        payment_method: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger payment processing workflow

        Handles:
        - Payment validation
        - Stripe charge creation
        - Receipt generation
        - Notification sending
        - Accounting record creation

        Args:
            tenant_id: Tenant ID
            amount: Payment amount
            payment_method: Payment method (card, ach, etc.)
            metadata: Additional metadata

        Returns:
            Workflow response or None on failure
        """
        payload = {
            "tenant_id": tenant_id,
            "amount": amount,
            "payment_method": payment_method,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        return await self.trigger_webhook("payment-process", payload)

    async def trigger_maintenance_scheduling(
        self,
        work_order_id: str,
        contractor_id: str,
        scheduled_date: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger maintenance scheduling workflow

        Handles:
        - Calendar integration (Cal.com)
        - Contractor notification
        - Tenant notification
        - Task creation (Vikunja)
        - Access instructions

        Args:
            work_order_id: Work order ID
            contractor_id: Contractor ID
            scheduled_date: Scheduled date/time
            metadata: Additional metadata

        Returns:
            Workflow response or None on failure
        """
        payload = {
            "work_order_id": work_order_id,
            "contractor_id": contractor_id,
            "scheduled_date": scheduled_date.isoformat(),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        return await self.trigger_webhook("maintenance-schedule", payload)

    async def trigger_tenant_communication(
        self,
        tenant_id: str,
        message_type: str,
        message_data: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger tenant communication workflow

        Handles multi-channel communication:
        - Email
        - SMS (Twilio)
        - In-app notification (Novu)
        - Push notification

        Args:
            tenant_id: Tenant ID
            message_type: Message type (payment_reminder, work_order_update, etc.)
            message_data: Message data
            channels: Channels to use (default: all)

        Returns:
            Workflow response or None on failure
        """
        payload = {
            "tenant_id": tenant_id,
            "message_type": message_type,
            "message_data": message_data,
            "channels": channels or ["email", "sms", "in_app"],
            "timestamp": datetime.now().isoformat()
        }

        return await self.trigger_webhook("tenant-communication", payload)


# ========================================
# Singleton instance management
# ========================================

_n8n_client: Optional[N8nClient] = None


def get_n8n_client(
    base_url: str = "http://n8n.ai.svc.cluster.local:5678",
    api_key: Optional[str] = None
) -> N8nClient:
    """Get singleton n8n client instance"""
    global _n8n_client
    if _n8n_client is None:
        _n8n_client = N8nClient(base_url=base_url, api_key=api_key)
    return _n8n_client


async def close_n8n_client():
    """Close singleton n8n client"""
    global _n8n_client
    if _n8n_client:
        await _n8n_client.close()
        _n8n_client = None
