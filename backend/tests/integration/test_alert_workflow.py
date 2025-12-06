"""
Integration tests for hub and alert workflows
"""
import pytest
from httpx import AsyncClient


class TestAlertWorkflow:
    """Test complete alert and incident management workflow"""

    @pytest.mark.asyncio
    async def test_alert_creation_and_acknowledgment(self, client: AsyncClient, admin_headers):
        """Test creating alerts and acknowledging them"""
        
        # Step 1: Create a property hub
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json={
                "name": "Alert Test Hub",
                "location": "Building A - Server Room",
                "hub_type": "property",
                "status": "online",
                "ip_address": "192.168.1.100"
            }
        )
        assert hub_response.status_code == 201
        hub = hub_response.json()
        hub_id = hub["id"]
        
        # Step 2: Create critical alert
        alert_response = await client.post(
            "/api/v1/alerts",
            headers=admin_headers,
            json={
                "hub_id": hub_id,
                "severity": "critical",
                "source": "kubernetes",
                "category": "deployment_failed",
                "message": "Pod deployment failed for wyoming-piper service",
                "status": "open"
            }
        )
        assert alert_response.status_code == 201
        alert = alert_response.json()
        alert_id = alert["id"]
        assert alert["severity"] == "critical"
        
        # Step 3: Acknowledge the alert
        ack_response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=admin_headers,
            json={
                "hub_id": hub_id,
                "severity": "critical",
                "source": "kubernetes",
                "category": "deployment_failed",
                "message": "Pod deployment failed for wyoming-piper service",
                "status": "acknowledged",
                "acknowledged_by": "admin@somnicluster.local"
            }
        )
        assert ack_response.status_code == 200
        ack_alert = ack_response.json()
        assert ack_alert["status"] == "acknowledged"
        assert ack_alert["acknowledged_by"] == "admin@somnicluster.local"
        
        # Step 4: Resolve the alert
        resolve_response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=admin_headers,
            json={
                "hub_id": hub_id,
                "severity": "critical",
                "source": "kubernetes",
                "category": "deployment_failed",
                "message": "Pod deployment failed for wyoming-piper service. RESOLVED.",
                "status": "resolved",
                "acknowledged_by": "admin@somnicluster.local"
            }
        )
        assert resolve_response.status_code == 200
        resolved_alert = resolve_response.json()
        assert resolved_alert["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_multiple_alerts_for_hub(self, client: AsyncClient, admin_headers):
        """Test managing multiple alerts for a single hub"""
        
        # Create hub
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json={
                "name": "Multi Alert Hub",
                "location": "Building B - Unit 101",
                "hub_type": "residential",
                "status": "online"
            }
        )
        hub_id = hub_response.json()["id"]
        
        # Create multiple alerts with different severities
        alert_configs = [
            {"severity": "info", "message": "System update available"},
            {"severity": "warning", "message": "Low disk space"},
            {"severity": "critical", "message": "Home Assistant offline"}
        ]
        
        alert_ids = []
        for config in alert_configs:
            alert_response = await client.post(
                "/api/v1/alerts",
                headers=admin_headers,
                json={
                    "hub_id": hub_id,
                    "severity": config["severity"],
                    "source": "monitoring",
                    "category": "system",
                    "message": config["message"],
                    "status": "open"
                }
            )
            assert alert_response.status_code == 201
            alert_ids.append(alert_response.json()["id"])
        
        # Filter alerts by hub
        hub_alerts_response = await client.get(
            f"/api/v1/alerts?hub_id={hub_id}",
            headers=admin_headers
        )
        assert hub_alerts_response.status_code == 200
        hub_alerts = hub_alerts_response.json()
        assert len(hub_alerts) >= 3
        
        # Filter critical alerts
        critical_alerts_response = await client.get(
            "/api/v1/alerts?severity=critical",
            headers=admin_headers
        )
        assert critical_alerts_response.status_code == 200
        critical_alerts = critical_alerts_response.json()
        assert len(critical_alerts) >= 1
        assert all(alert["severity"] == "critical" for alert in critical_alerts)
        
        # Filter open alerts
        open_alerts_response = await client.get(
            "/api/v1/alerts?status=open",
            headers=admin_headers
        )
        assert open_alerts_response.status_code == 200
        open_alerts = open_alerts_response.json()
        assert len(open_alerts) >= 3

    @pytest.mark.asyncio
    async def test_hub_status_change_workflow(self, client: AsyncClient, admin_headers):
        """Test hub going offline and generating alerts"""
        
        # Create hub
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json={
                "name": "Status Change Hub",
                "location": "Building C - Floor 2",
                "hub_type": "property",
                "status": "online"
            }
        )
        hub_id = hub_response.json()["id"]
        
        # Change hub status to offline
        update_response = await client.put(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers,
            json={
                "name": "Status Change Hub",
                "location": "Building C - Floor 2",
                "hub_type": "property",
                "status": "offline"
            }
        )
        assert update_response.status_code == 200
        updated_hub = update_response.json()
        assert updated_hub["status"] == "offline"
        
        # Create alert for hub being offline
        alert_response = await client.post(
            "/api/v1/alerts",
            headers=admin_headers,
            json={
                "hub_id": hub_id,
                "severity": "critical",
                "source": "monitoring",
                "category": "hub_offline",
                "message": "Hub Status Change Hub has gone offline",
                "status": "open"
            }
        )
        assert alert_response.status_code == 201
        
        # Bring hub back online
        online_response = await client.put(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers,
            json={
                "name": "Status Change Hub",
                "location": "Building C - Floor 2",
                "hub_type": "property",
                "status": "online"
            }
        )
        assert online_response.status_code == 200
        assert online_response.json()["status"] == "online"

    @pytest.mark.asyncio
    async def test_dashboard_alerts_integration(self, client: AsyncClient, admin_headers):
        """Test that alerts appear in dashboard metrics"""
        
        # Create hub
        hub_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json={
                "name": "Dashboard Alert Hub",
                "location": "Dashboard Location",
                "hub_type": "property",
                "status": "online"
            }
        )
        hub_id = hub_response.json()["id"]
        
        # Create critical alerts (should appear in dashboard)
        for i in range(3):
            await client.post(
                "/api/v1/alerts",
                headers=admin_headers,
                json={
                    "hub_id": hub_id,
                    "severity": "critical",
                    "source": "test",
                    "category": "test",
                    "message": f"Critical alert {i}",
                    "status": "open"
                }
            )
        
        # Check dashboard metrics
        dashboard_response = await client.get(
            "/api/v1/dashboard",
            headers=admin_headers
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        
        # Verify critical alerts count
        assert "critical_alerts_24h" in dashboard
        assert dashboard["critical_alerts_24h"] >= 3
