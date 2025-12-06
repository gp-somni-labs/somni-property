"""
Tests for Alerts API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestAlertsAPI:
    """Test Alerts CRUD operations and aggregation"""

    @pytest.mark.asyncio
    async def test_list_alerts(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/alerts returns list of alerts"""
        response = await client.get("/api/v1/alerts", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_alerts_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/alerts requires authentication"""
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_alert(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/alerts creates a new alert"""
        # Create a hub first
        hub_data = {
            "name": "Alert Test Hub",
            "location": "Test Location",
            "hub_type": "property",
            "status": "online"
        }
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = hub_response.json()["id"]
        
        # Create alert
        alert_data = {
            "hub_id": hub_id,
            "severity": "warning",
            "source": "home_assistant",
            "category": "device_offline",
            "message": "Smart thermostat offline",
            "status": "open"
        }
        
        response = await client.post(
            "/api/v1/alerts",
            headers=admin_headers,
            json=alert_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["hub_id"] == hub_id
        assert data["severity"] == "warning"
        assert data["message"] == alert_data["message"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_alert_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/alerts/{id} returns alert details"""
        # Create hub and alert
        hub_data = {
            "name": "Get Alert Hub",
            "location": "Get Location",
            "hub_type": "residential",
            "status": "online"
        }
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = hub_response.json()["id"]
        
        alert_data = {
            "hub_id": hub_id,
            "severity": "critical",
            "source": "kubernetes",
            "category": "deployment_failed",
            "message": "Pod deployment failed",
            "status": "open"
        }
        
        create_response = await client.post(
            "/api/v1/alerts",
            headers=admin_headers,
            json=alert_data
        )
        alert_id = create_response.json()["id"]
        
        # Get alert
        response = await client.get(
            f"/api/v1/alerts/{alert_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert_id
        assert data["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/alerts/{id} acknowledges alert"""
        # Create hub and alert
        hub_data = {
            "name": "Ack Alert Hub",
            "location": "Ack Location",
            "hub_type": "property",
            "status": "online"
        }
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = hub_response.json()["id"]
        
        alert_data = {
            "hub_id": hub_id,
            "severity": "info",
            "source": "monitoring",
            "category": "system_update",
            "message": "System update available",
            "status": "open"
        }
        
        create_response = await client.post(
            "/api/v1/alerts",
            headers=admin_headers,
            json=alert_data
        )
        alert_id = create_response.json()["id"]
        
        # Acknowledge alert
        update_data = {
            **alert_data,
            "status": "acknowledged",
            "acknowledged_by": "admin@example.com"
        }
        
        response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_by"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_filter_alerts_by_severity(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/alerts?severity={severity} filters by severity"""
        response = await client.get(
            "/api/v1/alerts?severity=critical",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(alert["severity"] == "critical" for alert in data)

    @pytest.mark.asyncio
    async def test_filter_alerts_by_status(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/alerts?status={status} filters by status"""
        response = await client.get(
            "/api/v1/alerts?status=open",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(alert["status"] == "open" for alert in data)

    @pytest.mark.asyncio
    async def test_filter_alerts_by_hub(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/alerts?hub_id={id} filters by hub"""
        # Create hub
        hub_data = {
            "name": "Filter Alert Hub",
            "location": "Filter Location",
            "hub_type": "property",
            "status": "online"
        }
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = hub_response.json()["id"]
        
        # Create multiple alerts for this hub
        for i in range(3):
            alert_data = {
                "hub_id": hub_id,
                "severity": "info",
                "source": "test",
                "category": "test_alert",
                "message": f"Test alert {i}",
                "status": "open"
            }
            await client.post("/api/v1/alerts", headers=admin_headers, json=alert_data)
        
        # Filter by hub
        response = await client.get(
            f"/api/v1/alerts?hub_id={hub_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all(alert["hub_id"] == hub_id for alert in data)
