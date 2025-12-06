"""
Vikunja Integration Client for SomniProperty

Integrates with self-hosted Vikunja (advanced task management) for:
- Converting work orders into actionable tasks
- Breaking multi-step repairs into subtasks
- Assigning tasks to contractors
- Tracking task progress and completion
- Project management for property improvements

Vikunja Service: vikunja.utilities.svc.cluster.local:3456
Documentation: https://vikunja.io/docs/
API Docs: https://try.vikunja.io/api/v1/docs
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Vikunja task priority levels"""
    UNSET = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    DO_NOW = 5


class VikunjaUser(BaseModel):
    """Vikunja user model"""
    id: int
    username: str
    name: str
    email: str


class VikunjaProject(BaseModel):
    """Vikunja project/list model"""
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    is_archived: bool = False
    hex_color: Optional[str] = None


class VikunjaTask(BaseModel):
    """Vikunja task model"""
    id: Optional[int] = None
    project_id: int
    title: str
    description: Optional[str] = None
    done: bool = False
    priority: int = TaskPriority.MEDIUM.value
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assignees: Optional[List[int]] = []
    labels: Optional[List[int]] = []
    parent_task_id: Optional[int] = None
    percent_done: float = 0.0
    related_tasks: Optional[Dict[str, Any]] = {}


class VikunjaLabel(BaseModel):
    """Vikunja label model"""
    id: Optional[int] = None
    title: str
    hex_color: Optional[str] = None
    description: Optional[str] = None


class VikunjaClient:
    """Client for interacting with Vikunja API"""

    def __init__(
        self,
        base_url: str = "http://vikunja.utilities.svc.cluster.local:3456",
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Vikunja client

        Args:
            base_url: Vikunja service URL
            username: Vikunja username for login
            password: Vikunja password for login
            api_token: API token (alternative to username/password)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def login(self) -> bool:
        """
        Login to Vikunja and get API token

        Returns:
            True if login successful, False otherwise
        """
        if self.api_token:
            return True  # Already have token

        if not self.username or not self.password:
            logger.error("No credentials provided for Vikunja login")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/login",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.api_token = data.get("token")
                logger.info("Successfully logged in to Vikunja")
                return True
            else:
                logger.error(f"Vikunja login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error logging in to Vikunja: {e}")
            return False

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    # ========================================
    # Project Management
    # ========================================

    async def create_project(
        self,
        title: str,
        description: Optional[str] = None,
        hex_color: Optional[str] = None
    ) -> Optional[VikunjaProject]:
        """
        Create a project in Vikunja

        Use for organizing tasks by:
        - Property (e.g., "Sunset Apartments")
        - Building (e.g., "Building A Maintenance")
        - Type (e.g., "HVAC Projects", "Plumbing Work")

        Args:
            title: Project title
            description: Project description
            hex_color: Project color (e.g., "#3498db")

        Returns:
            Created project or None on failure
        """
        try:
            if not self.api_token and not await self.login():
                return None

            payload = {
                "title": title,
                "description": description or ""
            }
            if hex_color:
                payload["hex_color"] = hex_color

            response = await self.client.put(
                f"{self.base_url}/api/v1/projects",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return VikunjaProject(
                    id=data.get("id"),
                    title=data.get("title"),
                    description=data.get("description"),
                    is_archived=data.get("is_archived", False),
                    hex_color=data.get("hex_color")
                )
            else:
                logger.error(f"Failed to create project: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None

    async def get_project(self, project_id: int) -> Optional[VikunjaProject]:
        """Get project by ID"""
        try:
            if not self.api_token and not await self.login():
                return None

            response = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return VikunjaProject(
                    id=data.get("id"),
                    title=data.get("title"),
                    description=data.get("description"),
                    is_archived=data.get("is_archived", False),
                    hex_color=data.get("hex_color")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None

    async def list_projects(self) -> List[VikunjaProject]:
        """List all projects"""
        try:
            if not self.api_token and not await self.login():
                return []

            response = await self.client.get(
                f"{self.base_url}/api/v1/projects",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    VikunjaProject(
                        id=project.get("id"),
                        title=project.get("title"),
                        description=project.get("description"),
                        is_archived=project.get("is_archived", False),
                        hex_color=project.get("hex_color")
                    )
                    for project in data
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []

    # ========================================
    # Task Management
    # ========================================

    async def create_task(self, task: VikunjaTask) -> Optional[VikunjaTask]:
        """
        Create a task in Vikunja

        Use for:
        - Work orders → Tasks
        - Multi-step repairs → Parent task with subtasks
        - Recurring maintenance → Recurring tasks

        Args:
            task: Task details

        Returns:
            Created task or None on failure
        """
        try:
            if not self.api_token and not await self.login():
                return None

            payload = {
                "title": task.title,
                "description": task.description or "",
                "done": task.done,
                "priority": task.priority,
                "percent_done": task.percent_done
            }

            if task.due_date:
                payload["due_date"] = task.due_date.isoformat()
            if task.start_date:
                payload["start_date"] = task.start_date.isoformat()
            if task.end_date:
                payload["end_date"] = task.end_date.isoformat()
            if task.assignees:
                payload["assignees"] = [{"id": user_id} for user_id in task.assignees]
            if task.labels:
                payload["labels"] = [{"id": label_id} for label_id in task.labels]
            if task.parent_task_id:
                payload["parent_task_id"] = task.parent_task_id

            response = await self.client.put(
                f"{self.base_url}/api/v1/projects/{task.project_id}/tasks",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return VikunjaTask(
                    id=data.get("id"),
                    project_id=data.get("project_id"),
                    title=data.get("title"),
                    description=data.get("description"),
                    done=data.get("done", False),
                    priority=data.get("priority", TaskPriority.MEDIUM.value),
                    percent_done=data.get("percent_done", 0.0)
                )
            else:
                logger.error(f"Failed to create task: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    async def update_task(self, task_id: int, updates: Dict[str, Any]) -> Optional[VikunjaTask]:
        """
        Update a task

        Args:
            task_id: Task ID
            updates: Fields to update (e.g., {"done": True, "percent_done": 100})

        Returns:
            Updated task or None on failure
        """
        try:
            if not self.api_token and not await self.login():
                return None

            response = await self.client.post(
                f"{self.base_url}/api/v1/tasks/{task_id}",
                headers=self._headers(),
                json=updates
            )

            if response.status_code == 200:
                data = response.json()
                return VikunjaTask(
                    id=data.get("id"),
                    project_id=data.get("project_id"),
                    title=data.get("title"),
                    description=data.get("description"),
                    done=data.get("done", False),
                    priority=data.get("priority", TaskPriority.MEDIUM.value),
                    percent_done=data.get("percent_done", 0.0)
                )
            else:
                logger.error(f"Failed to update task: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None

    async def get_task(self, task_id: int) -> Optional[VikunjaTask]:
        """Get task by ID"""
        try:
            if not self.api_token and not await self.login():
                return None

            response = await self.client.get(
                f"{self.base_url}/api/v1/tasks/{task_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return VikunjaTask(
                    id=data.get("id"),
                    project_id=data.get("project_id"),
                    title=data.get("title"),
                    description=data.get("description"),
                    done=data.get("done", False),
                    priority=data.get("priority", TaskPriority.MEDIUM.value),
                    percent_done=data.get("percent_done", 0.0)
                )
            return None

        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    async def list_tasks(
        self,
        project_id: int,
        filter_done: Optional[bool] = None
    ) -> List[VikunjaTask]:
        """
        List tasks in a project

        Args:
            project_id: Project ID
            filter_done: Filter by done status (None = all, True = done, False = not done)

        Returns:
            List of tasks
        """
        try:
            if not self.api_token and not await self.login():
                return []

            params = {}
            if filter_done is not None:
                params["filter_by"] = "done"
                params["filter_value"] = str(filter_done).lower()

            response = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}/tasks",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    VikunjaTask(
                        id=task.get("id"),
                        project_id=task.get("project_id"),
                        title=task.get("title"),
                        description=task.get("description"),
                        done=task.get("done", False),
                        priority=task.get("priority", TaskPriority.MEDIUM.value),
                        percent_done=task.get("percent_done", 0.0)
                    )
                    for task in data
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    async def create_subtask(
        self,
        parent_task_id: int,
        title: str,
        description: Optional[str] = None
    ) -> Optional[VikunjaTask]:
        """
        Create a subtask

        Use for breaking down complex work orders:
        - Parent: "Replace HVAC system in Unit 204"
          - Subtask 1: "Remove old HVAC unit"
          - Subtask 2: "Install new HVAC unit"
          - Subtask 3: "Test system operation"
          - Subtask 4: "Clean up work area"

        Args:
            parent_task_id: Parent task ID
            title: Subtask title
            description: Subtask description

        Returns:
            Created subtask or None on failure
        """
        try:
            # First get parent task to get project_id
            parent = await self.get_task(parent_task_id)
            if not parent:
                logger.error(f"Parent task {parent_task_id} not found")
                return None

            # Create subtask with parent reference
            subtask = VikunjaTask(
                project_id=parent.project_id,
                title=title,
                description=description,
                parent_task_id=parent_task_id,
                priority=parent.priority  # Inherit priority from parent
            )

            return await self.create_task(subtask)

        except Exception as e:
            logger.error(f"Error creating subtask: {e}")
            return None

    # ========================================
    # Label Management
    # ========================================

    async def create_label(
        self,
        title: str,
        hex_color: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[VikunjaLabel]:
        """
        Create a label

        Use for categorizing tasks:
        - "urgent", "maintenance", "hvac", "plumbing", "electrical"
        - "unit-204", "building-a", "common-area"
        - "contractor-assigned", "awaiting-parts", "on-hold"

        Args:
            title: Label title
            hex_color: Label color (e.g., "#e74c3c")
            description: Label description

        Returns:
            Created label or None on failure
        """
        try:
            if not self.api_token and not await self.login():
                return None

            payload = {
                "title": title,
                "description": description or ""
            }
            if hex_color:
                payload["hex_color"] = hex_color

            response = await self.client.put(
                f"{self.base_url}/api/v1/labels",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return VikunjaLabel(
                    id=data.get("id"),
                    title=data.get("title"),
                    hex_color=data.get("hex_color"),
                    description=data.get("description")
                )
            else:
                logger.error(f"Failed to create label: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating label: {e}")
            return None

    async def list_labels(self) -> List[VikunjaLabel]:
        """List all labels"""
        try:
            if not self.api_token and not await self.login():
                return []

            response = await self.client.get(
                f"{self.base_url}/api/v1/labels",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    VikunjaLabel(
                        id=label.get("id"),
                        title=label.get("title"),
                        hex_color=label.get("hex_color"),
                        description=label.get("description")
                    )
                    for label in data
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            return []

    # ========================================
    # Work Order Integration
    # ========================================

    async def create_work_order_task(
        self,
        project_id: int,
        work_order_id: str,
        work_order_title: str,
        work_order_description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        assignee_ids: Optional[List[int]] = None,
        subtasks: Optional[List[str]] = None
    ) -> Optional[VikunjaTask]:
        """
        Create a Vikunja task from a SomniProperty work order

        Automatically creates:
        - Main task for work order
        - Subtasks if multi-step work
        - Labels for categorization

        Args:
            project_id: Vikunja project ID
            work_order_id: SomniProperty work order ID
            work_order_title: Work order title
            work_order_description: Work order description
            priority: Task priority
            due_date: Due date
            assignee_ids: List of Vikunja user IDs to assign
            subtasks: Optional list of subtask titles

        Returns:
            Created main task or None on failure
        """
        try:
            # Create main task
            main_task = VikunjaTask(
                project_id=project_id,
                title=f"WO-{work_order_id}: {work_order_title}",
                description=work_order_description,
                priority=priority.value,
                due_date=due_date,
                assignees=assignee_ids or []
            )

            created_task = await self.create_task(main_task)

            if not created_task:
                return None

            # Create subtasks if provided
            if subtasks and created_task.id:
                for subtask_title in subtasks:
                    await self.create_subtask(
                        parent_task_id=created_task.id,
                        title=subtask_title
                    )

            return created_task

        except Exception as e:
            logger.error(f"Error creating work order task: {e}")
            return None

    async def mark_task_complete(self, task_id: int) -> bool:
        """
        Mark a task as complete

        Args:
            task_id: Task ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.update_task(
                task_id=task_id,
                updates={
                    "done": True,
                    "percent_done": 100.0,
                    "end_date": datetime.now().isoformat()
                }
            )
            return result is not None

        except Exception as e:
            logger.error(f"Error marking task complete: {e}")
            return False


# ========================================
# Singleton instance management
# ========================================

_vikunja_client: Optional[VikunjaClient] = None


def get_vikunja_client(
    base_url: str = "http://vikunja.utilities.svc.cluster.local:3456",
    username: Optional[str] = None,
    password: Optional[str] = None,
    api_token: Optional[str] = None
) -> VikunjaClient:
    """Get singleton Vikunja client instance"""
    global _vikunja_client
    if _vikunja_client is None:
        _vikunja_client = VikunjaClient(
            base_url=base_url,
            username=username,
            password=password,
            api_token=api_token
        )
    return _vikunja_client


async def close_vikunja_client():
    """Close singleton Vikunja client"""
    global _vikunja_client
    if _vikunja_client:
        await _vikunja_client.close()
        _vikunja_client = None
