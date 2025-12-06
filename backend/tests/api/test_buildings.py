"""
Tests for Buildings API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestBuildingsAPI:
    """Test Buildings CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_buildings(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/buildings returns list of buildings"""
        response = await client.get("/api/v1/buildings", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_buildings_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/buildings requires authentication"""
        response = await client.get("/api/v1/buildings")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_building(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/buildings creates a new building"""
        building_data = {
            "name": "Test Building",
            "address": "123 Test St",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "building_type": "residential",
            "total_units": 10
        }
        
        response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == building_data["name"]
        assert data["address"] == building_data["address"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_building_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/buildings/{id} returns building details"""
        # First create a building
        building_data = {
            "name": "Test Building for Get",
            "address": "456 Get St",
            "city": "Get City",
            "state": "NY",
            "zip_code": "54321",
            "building_type": "commercial",
            "total_units": 5
        }
        
        create_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = create_response.json()["id"]
        
        # Now get it
        response = await client.get(
            f"/api/v1/buildings/{building_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == building_id
        assert data["name"] == building_data["name"]

    @pytest.mark.asyncio
    async def test_update_building(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/buildings/{id} updates building"""
        # Create a building first
        building_data = {
            "name": "Original Name",
            "address": "789 Update St",
            "city": "Update City",
            "state": "TX",
            "zip_code": "78901",
            "building_type": "residential",
            "total_units": 8
        }
        
        create_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            **building_data,
            "name": "Updated Name",
            "total_units": 12
        }
        
        response = await client.put(
            f"/api/v1/buildings/{building_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["total_units"] == 12

    @pytest.mark.asyncio
    async def test_delete_building(self, client: AsyncClient, admin_headers):
        """Test DELETE /api/v1/buildings/{id} deletes building"""
        # Create a building first
        building_data = {
            "name": "Building to Delete",
            "address": "999 Delete St",
            "city": "Delete City",
            "state": "FL",
            "zip_code": "99999",
            "building_type": "residential",
            "total_units": 3
        }
        
        create_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(
            f"/api/v1/buildings/{building_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/buildings/{building_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_building(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/buildings/{id} with invalid ID returns 404"""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/buildings/{fake_id}",
            headers=admin_headers
        )
        assert response.status_code == 404
