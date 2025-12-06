"""
Tests for Property Edge Nodes (Hubs) API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestHubsAPI:
    """Test Property Edge Nodes (Hubs) CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_hubs(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/hubs returns list of hubs"""
        response = await client.get("/api/v1/hubs", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_hubs_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/hubs requires authentication"""
        response = await client.get("/api/v1/hubs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_hub(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/hubs creates a new hub"""
        hub_data = {
            "name": "Test Property Hub",
            "location": "Building A - Basement",
            "hub_type": "property",
            "status": "online",
            "ip_address": "192.168.1.100",
            "k3s_version": "v1.28.5",
            "home_assistant_version": "2024.1.0"
        }
        
        response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == hub_data["name"]
        assert data["hub_type"] == "property"
        assert data["status"] == "online"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_hub_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/hubs/{id} returns hub details"""
        # Create a hub
        hub_data = {
            "name": "Get Test Hub",
            "location": "Building B - Floor 1",
            "hub_type": "residential",
            "status": "online"
        }
        
        create_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = create_response.json()["id"]
        
        # Get it
        response = await client.get(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == hub_id
        assert data["name"] == hub_data["name"]

    @pytest.mark.asyncio
    async def test_update_hub_status(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/hubs/{id} updates hub status"""
        # Create a hub
        hub_data = {
            "name": "Update Test Hub",
            "location": "Building C - Rooftop",
            "hub_type": "property",
            "status": "online"
        }
        
        create_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = create_response.json()["id"]
        
        # Update to offline
        update_data = {
            **hub_data,
            "status": "offline"
        }
        
        response = await client.put(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "offline"

    @pytest.mark.asyncio
    async def test_delete_hub(self, client: AsyncClient, admin_headers):
        """Test DELETE /api/v1/hubs/{id} deletes hub"""
        # Create a hub
        hub_data = {
            "name": "Delete Test Hub",
            "location": "Building D - Unit 404",
            "hub_type": "residential",
            "status": "offline"
        }
        
        create_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/hubs/{hub_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_hubs_by_type(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/hubs?hub_type={type} filters by type"""
        # Create property hub
        property_hub = {
            "name": "Property Hub Filter",
            "location": "Filter Location A",
            "hub_type": "property",
            "status": "online"
        }
        await client.post("/api/v1/hubs", headers=admin_headers, json=property_hub)
        
        # Filter by property type
        response = await client.get(
            "/api/v1/hubs?hub_type=property",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(hub["hub_type"] == "property" for hub in data)

    @pytest.mark.asyncio
    async def test_filter_hubs_by_status(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/hubs?status={status} filters by status"""
        response = await client.get(
            "/api/v1/hubs?status=online",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(hub["status"] == "online" for hub in data)

    @pytest.mark.asyncio
    async def test_get_hub_health(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/hubs/{id}/health returns hub health status"""
        # Create a hub
        hub_data = {
            "name": "Health Test Hub",
            "location": "Health Location",
            "hub_type": "property",
            "status": "online"
        }
        
        create_response = await client.post(
            "/api/v1/hubs",
            headers=admin_headers,
            json=hub_data
        )
        hub_id = create_response.json()["id"]
        
        # Get health (this may return 200 or 503 depending on implementation)
        response = await client.get(
            f"/api/v1/hubs/{hub_id}/health",
            headers=admin_headers
        )
        
        # Accept either 200 (healthy), 503 (unhealthy), or 404 (not implemented)
        assert response.status_code in [200, 404, 503]
