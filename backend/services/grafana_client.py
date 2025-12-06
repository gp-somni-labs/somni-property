"""
Grafana Integration Client for SomniProperty

Integrates with self-hosted Grafana (analytics and dashboards) for:
- Creating and managing dashboards
- Building visualization panels
- Setting up alerts and notifications
- Managing data sources
- Property analytics and KPIs
- Operational insights

Grafana Service: grafana.monitoring.svc.cluster.local
Documentation: https://grafana.com/docs/
API Docs: https://grafana.com/docs/grafana/latest/developers/http_api/
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PanelType(Enum):
    """Grafana panel types"""
    GRAPH = "graph"
    STAT = "stat"
    GAUGE = "gauge"
    TABLE = "table"
    TIMESERIES = "timeseries"
    BAR_CHART = "barchart"
    PIE_CHART = "piechart"
    HEATMAP = "heatmap"
    ALERT_LIST = "alertlist"
    LOGS = "logs"


class AlertState(Enum):
    """Grafana alert states"""
    OK = "ok"
    PENDING = "pending"
    ALERTING = "alerting"
    NO_DATA = "no_data"
    ERROR = "error"


class DataSourceType(Enum):
    """Grafana data source types"""
    PROMETHEUS = "prometheus"
    INFLUXDB = "influxdb"
    MYSQL = "mysql"
    POSTGRES = "postgres"
    ELASTICSEARCH = "elasticsearch"
    GRAPHITE = "graphite"
    CLOUDWATCH = "cloudwatch"
    LOKI = "loki"
    TEMPO = "tempo"


class GrafanaDashboard(BaseModel):
    """Grafana dashboard model"""
    uid: Optional[str] = None
    title: str
    tags: Optional[List[str]] = []
    timezone: str = "browser"
    refresh: str = "30s"
    time_from: str = "now-6h"
    time_to: str = "now"
    panels: Optional[List[Dict[str, Any]]] = []
    variables: Optional[List[Dict[str, Any]]] = []


class GrafanaPanel(BaseModel):
    """Grafana panel model"""
    id: Optional[int] = None
    title: str
    type: str = PanelType.TIMESERIES.value
    gridPos: Dict[str, int] = {"x": 0, "y": 0, "w": 12, "h": 8}
    targets: Optional[List[Dict[str, Any]]] = []
    options: Optional[Dict[str, Any]] = {}
    fieldConfig: Optional[Dict[str, Any]] = {}


class GrafanaDataSource(BaseModel):
    """Grafana data source model"""
    id: Optional[int] = None
    uid: Optional[str] = None
    name: str
    type: str
    url: str
    access: str = "proxy"
    is_default: bool = False
    json_data: Optional[Dict[str, Any]] = {}


class GrafanaAlert(BaseModel):
    """Grafana alert model"""
    id: Optional[int] = None
    dashboard_uid: str
    panel_id: int
    name: str
    message: str
    state: str = AlertState.OK.value
    conditions: Optional[List[Dict[str, Any]]] = []
    notifications: Optional[List[int]] = []


class GrafanaClient:
    """Client for interacting with Grafana API"""

    def __init__(
        self,
        base_url: str = "http://grafana.monitoring.svc.cluster.local:3000",
        api_key: Optional[str] = None,
        username: Optional[str] = "admin",
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Grafana client

        Args:
            base_url: Grafana service URL
            api_key: Grafana API key (from Configuration → API Keys)
            username: Grafana username (fallback if no API key)
            password: Grafana password (fallback if no API key)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
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
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _auth(self) -> Optional[tuple]:
        """Get basic auth credentials if no API key"""
        if not self.api_key and self.username and self.password:
            return (self.username, self.password)
        return None

    # ========================================
    # Dashboard Management
    # ========================================

    async def create_dashboard(
        self,
        dashboard: GrafanaDashboard,
        folder_id: Optional[int] = 0,
        overwrite: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update a dashboard

        Args:
            dashboard: Dashboard configuration
            folder_id: Folder ID (0 = General folder)
            overwrite: Overwrite existing dashboard with same UID

        Returns:
            Created dashboard info or None on failure
        """
        try:
            payload = {
                "dashboard": {
                    "uid": dashboard.uid,
                    "title": dashboard.title,
                    "tags": dashboard.tags or [],
                    "timezone": dashboard.timezone,
                    "refresh": dashboard.refresh,
                    "time": {
                        "from": dashboard.time_from,
                        "to": dashboard.time_to
                    },
                    "panels": dashboard.panels or [],
                    "templating": {
                        "list": dashboard.variables or []
                    }
                },
                "folderId": folder_id,
                "overwrite": overwrite
            }

            response = await self.client.post(
                f"{self.base_url}/api/dashboards/db",
                headers=self._headers(),
                auth=self._auth(),
                json=payload
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to create dashboard: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return None

    async def get_dashboard(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get dashboard by UID

        Args:
            uid: Dashboard UID

        Returns:
            Dashboard configuration or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/dashboards/uid/{uid}",
                headers=self._headers(),
                auth=self._auth()
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Error getting dashboard: {e}")
            return None

    async def delete_dashboard(self, uid: str) -> bool:
        """
        Delete dashboard by UID

        Args:
            uid: Dashboard UID

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/dashboards/uid/{uid}",
                headers=self._headers(),
                auth=self._auth()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error deleting dashboard: {e}")
            return False

    async def search_dashboards(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        folder_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search dashboards

        Args:
            query: Search query
            tags: Filter by tags
            folder_ids: Filter by folder IDs

        Returns:
            List of matching dashboards
        """
        try:
            params = {}
            if query:
                params["query"] = query
            if tags:
                params["tag"] = tags
            if folder_ids:
                params["folderIds"] = folder_ids

            response = await self.client.get(
                f"{self.base_url}/api/search",
                headers=self._headers(),
                auth=self._auth(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.error(f"Error searching dashboards: {e}")
            return []

    # ========================================
    # Panel Building Helpers
    # ========================================

    def build_panel(
        self,
        title: str,
        panel_type: PanelType = PanelType.TIMESERIES,
        queries: Optional[List[Dict[str, Any]]] = None,
        x: int = 0,
        y: int = 0,
        width: int = 12,
        height: int = 8
    ) -> Dict[str, Any]:
        """
        Build a panel configuration

        Args:
            title: Panel title
            panel_type: Panel type
            queries: List of data source queries
            x: Grid X position
            y: Grid Y position
            width: Panel width (1-24)
            height: Panel height

        Returns:
            Panel configuration dict
        """
        return {
            "title": title,
            "type": panel_type.value,
            "gridPos": {
                "x": x,
                "y": y,
                "w": width,
                "h": height
            },
            "targets": queries or [],
            "options": {},
            "fieldConfig": {
                "defaults": {},
                "overrides": []
            }
        }

    def build_prometheus_query(
        self,
        query: str,
        legend: str = "",
        ref_id: str = "A"
    ) -> Dict[str, Any]:
        """
        Build a Prometheus query for a panel

        Args:
            query: PromQL query
            legend: Legend format
            ref_id: Query reference ID

        Returns:
            Query configuration dict
        """
        return {
            "refId": ref_id,
            "expr": query,
            "legendFormat": legend,
            "datasource": {
                "type": "prometheus"
            }
        }

    # ========================================
    # Data Source Management
    # ========================================

    async def create_datasource(
        self,
        datasource: GrafanaDataSource
    ) -> Optional[GrafanaDataSource]:
        """
        Create a data source

        Args:
            datasource: Data source configuration

        Returns:
            Created data source or None on failure
        """
        try:
            payload = {
                "name": datasource.name,
                "type": datasource.type,
                "url": datasource.url,
                "access": datasource.access,
                "isDefault": datasource.is_default,
                "jsonData": datasource.json_data or {}
            }

            response = await self.client.post(
                f"{self.base_url}/api/datasources",
                headers=self._headers(),
                auth=self._auth(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                return GrafanaDataSource(
                    id=data.get("id"),
                    uid=data.get("uid"),
                    name=data.get("name"),
                    type=data.get("type"),
                    url=data.get("url"),
                    access=data.get("access"),
                    is_default=data.get("isDefault", False),
                    json_data=data.get("jsonData", {})
                )
            else:
                logger.error(f"Failed to create datasource: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating datasource: {e}")
            return None

    async def get_datasources(self) -> List[GrafanaDataSource]:
        """
        Get all data sources

        Returns:
            List of data sources
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/datasources",
                headers=self._headers(),
                auth=self._auth()
            )

            if response.status_code == 200:
                datasources = response.json()
                return [
                    GrafanaDataSource(
                        id=ds.get("id"),
                        uid=ds.get("uid"),
                        name=ds.get("name"),
                        type=ds.get("type"),
                        url=ds.get("url"),
                        access=ds.get("access"),
                        is_default=ds.get("isDefault", False),
                        json_data=ds.get("jsonData", {})
                    )
                    for ds in datasources
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting datasources: {e}")
            return []

    async def delete_datasource(self, datasource_id: int) -> bool:
        """
        Delete a data source

        Args:
            datasource_id: Data source ID

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/datasources/{datasource_id}",
                headers=self._headers(),
                auth=self._auth()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error deleting datasource: {e}")
            return False

    # ========================================
    # Alert Management
    # ========================================

    async def create_alert(
        self,
        alert: GrafanaAlert
    ) -> Optional[Dict[str, Any]]:
        """
        Create an alert rule

        Args:
            alert: Alert configuration

        Returns:
            Created alert or None on failure
        """
        try:
            payload = {
                "dashboardUid": alert.dashboard_uid,
                "panelId": alert.panel_id,
                "name": alert.name,
                "message": alert.message,
                "conditions": alert.conditions or [],
                "notifications": alert.notifications or []
            }

            response = await self.client.post(
                f"{self.base_url}/api/alerts",
                headers=self._headers(),
                auth=self._auth(),
                json=payload
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to create alert: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None

    async def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Get all alerts

        Returns:
            List of alerts
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/alerts",
                headers=self._headers(),
                auth=self._auth()
            )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    async def pause_alert(self, alert_id: int, paused: bool = True) -> bool:
        """
        Pause or resume an alert

        Args:
            alert_id: Alert ID
            paused: True to pause, False to resume

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"paused": paused}

            response = await self.client.post(
                f"{self.base_url}/api/alerts/{alert_id}/pause",
                headers=self._headers(),
                auth=self._auth(),
                json=payload
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error pausing alert: {e}")
            return False

    # ========================================
    # Annotation Management
    # ========================================

    async def create_annotation(
        self,
        dashboard_uid: Optional[str] = None,
        panel_id: Optional[int] = None,
        time: Optional[int] = None,
        time_end: Optional[int] = None,
        tags: Optional[List[str]] = None,
        text: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Create an annotation

        Use for marking events on dashboards:
        - Deployments
        - Incidents
        - Maintenance windows
        - Work order completions

        Args:
            dashboard_uid: Dashboard UID (optional)
            panel_id: Panel ID (optional)
            time: Start time (Unix milliseconds)
            time_end: End time for regions (Unix milliseconds)
            tags: Annotation tags
            text: Annotation text

        Returns:
            Created annotation or None on failure
        """
        try:
            payload = {
                "text": text,
                "tags": tags or []
            }

            if dashboard_uid:
                payload["dashboardUID"] = dashboard_uid
            if panel_id:
                payload["panelId"] = panel_id
            if time:
                payload["time"] = time
            if time_end:
                payload["timeEnd"] = time_end

            response = await self.client.post(
                f"{self.base_url}/api/annotations",
                headers=self._headers(),
                auth=self._auth(),
                json=payload
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to create annotation: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating annotation: {e}")
            return None

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def create_property_dashboard(
        self,
        property_id: str,
        property_name: str,
        prometheus_url: str = "http://prometheus.monitoring.svc.cluster.local:9090"
    ) -> Optional[str]:
        """
        Create a comprehensive property management dashboard

        Includes panels for:
        - Occupancy rate
        - Rent collection rate
        - Work order metrics
        - Maintenance costs
        - Tenant satisfaction
        - Property health score

        Args:
            property_id: Property ID
            property_name: Property display name
            prometheus_url: Prometheus data source URL

        Returns:
            Dashboard UID or None on failure
        """
        try:
            # Create panels
            panels = []

            # Occupancy rate panel
            panels.append(self.build_panel(
                title="Occupancy Rate",
                panel_type=PanelType.GAUGE,
                queries=[self.build_prometheus_query(
                    query=f'property_occupancy_rate{{property_id="{property_id}"}}',
                    legend="Occupancy"
                )],
                x=0, y=0, width=6, height=8
            ))

            # Rent collection rate panel
            panels.append(self.build_panel(
                title="Rent Collection Rate",
                panel_type=PanelType.GAUGE,
                queries=[self.build_prometheus_query(
                    query=f'property_rent_collection_rate{{property_id="{property_id}"}}',
                    legend="Collection Rate"
                )],
                x=6, y=0, width=6, height=8
            ))

            # Work orders over time
            panels.append(self.build_panel(
                title="Work Orders Over Time",
                panel_type=PanelType.TIMESERIES,
                queries=[self.build_prometheus_query(
                    query=f'rate(property_work_orders_total{{property_id="{property_id}"}}[1h])',
                    legend="Work Orders/hour"
                )],
                x=0, y=8, width=12, height=8
            ))

            # Maintenance costs
            panels.append(self.build_panel(
                title="Maintenance Costs",
                panel_type=PanelType.BAR_CHART,
                queries=[self.build_prometheus_query(
                    query=f'property_maintenance_cost_total{{property_id="{property_id}"}}',
                    legend="Total Cost"
                )],
                x=12, y=0, width=12, height=8
            ))

            # Active work orders by status
            panels.append(self.build_panel(
                title="Work Orders by Status",
                panel_type=PanelType.PIE_CHART,
                queries=[self.build_prometheus_query(
                    query=f'property_work_orders_by_status{{property_id="{property_id}"}}',
                    legend="{{status}}"
                )],
                x=12, y=8, width=12, height=8
            ))

            # Create dashboard
            dashboard = GrafanaDashboard(
                uid=f"property-{property_id}",
                title=f"Property Dashboard - {property_name}",
                tags=["property", "somni-property", property_id],
                panels=panels
            )

            result = await self.create_dashboard(dashboard, overwrite=True)
            if result:
                return result.get("uid")
            return None

        except Exception as e:
            logger.error(f"Error creating property dashboard: {e}")
            return None

    async def create_unit_dashboard(
        self,
        property_id: str,
        unit_id: str,
        unit_name: str
    ) -> Optional[str]:
        """
        Create a unit-specific dashboard

        Includes panels for:
        - IoT sensor data (temperature, humidity, etc.)
        - Energy consumption
        - Device status
        - Work order history
        - Tenant activity

        Args:
            property_id: Property ID
            unit_id: Unit ID
            unit_name: Unit display name

        Returns:
            Dashboard UID or None on failure
        """
        try:
            panels = []

            # Temperature sensor
            panels.append(self.build_panel(
                title="Temperature",
                panel_type=PanelType.TIMESERIES,
                queries=[self.build_prometheus_query(
                    query=f'unit_temperature{{property_id="{property_id}",unit_id="{unit_id}"}}',
                    legend="Temperature (°F)"
                )],
                x=0, y=0, width=12, height=8
            ))

            # Humidity sensor
            panels.append(self.build_panel(
                title="Humidity",
                panel_type=PanelType.TIMESERIES,
                queries=[self.build_prometheus_query(
                    query=f'unit_humidity{{property_id="{property_id}",unit_id="{unit_id}"}}',
                    legend="Humidity (%)"
                )],
                x=12, y=0, width=12, height=8
            ))

            # Energy consumption
            panels.append(self.build_panel(
                title="Energy Consumption",
                panel_type=PanelType.TIMESERIES,
                queries=[self.build_prometheus_query(
                    query=f'rate(unit_energy_consumption_kwh{{property_id="{property_id}",unit_id="{unit_id}"}}[1h])',
                    legend="kWh/hour"
                )],
                x=0, y=8, width=12, height=8
            ))

            # Device status
            panels.append(self.build_panel(
                title="Connected Devices",
                panel_type=PanelType.STAT,
                queries=[self.build_prometheus_query(
                    query=f'unit_devices_online{{property_id="{property_id}",unit_id="{unit_id}"}}',
                    legend="Online"
                )],
                x=12, y=8, width=6, height=8
            ))

            dashboard = GrafanaDashboard(
                uid=f"unit-{property_id}-{unit_id}",
                title=f"Unit Dashboard - {unit_name}",
                tags=["unit", "somni-property", property_id, unit_id],
                panels=panels
            )

            result = await self.create_dashboard(dashboard, overwrite=True)
            if result:
                return result.get("uid")
            return None

        except Exception as e:
            logger.error(f"Error creating unit dashboard: {e}")
            return None

    async def create_work_order_annotation(
        self,
        work_order_id: str,
        work_order_title: str,
        completed_at: datetime,
        property_id: Optional[str] = None
    ) -> bool:
        """
        Create an annotation for a completed work order

        Args:
            work_order_id: Work order ID
            work_order_title: Work order title
            completed_at: Completion timestamp
            property_id: Property ID (for property-specific dashboard)

        Returns:
            True if annotation created, False otherwise
        """
        try:
            dashboard_uid = f"property-{property_id}" if property_id else None

            result = await self.create_annotation(
                dashboard_uid=dashboard_uid,
                time=int(completed_at.timestamp() * 1000),
                tags=["work-order", work_order_id],
                text=f"Work Order Completed: {work_order_title}"
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error creating work order annotation: {e}")
            return False


# ========================================
# Singleton instance management
# ========================================

_grafana_client: Optional[GrafanaClient] = None


def get_grafana_client(
    base_url: str = "http://grafana.monitoring.svc.cluster.local:3000",
    api_key: Optional[str] = None,
    username: str = "admin",
    password: Optional[str] = None
) -> GrafanaClient:
    """Get singleton Grafana client instance"""
    global _grafana_client
    if _grafana_client is None:
        _grafana_client = GrafanaClient(
            base_url=base_url,
            api_key=api_key,
            username=username,
            password=password
        )
    return _grafana_client


async def close_grafana_client():
    """Close singleton Grafana client"""
    global _grafana_client
    if _grafana_client:
        await _grafana_client.close()
        _grafana_client = None
