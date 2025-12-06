"""
Tests for Units API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestUnitsAPI:
    """Test Units CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_units(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/units returns list of units"""
        response = await client.get("/api/v1/units", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_units_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/units requires authentication"""
        response = await client.get("/api/v1/units")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_unit(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/units creates a new unit"""
        # First create a building
        building_data = {
            "name": "Test Building for Units",
            "address": "123 Unit Test St",
            "city": "Unit City",
            "state": "CA",
            "zip_code": "12345",
            "building_type": "residential",
            "total_units": 10
        }
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = building_response.json()["id"]
        
        # Now create a unit
        unit_data = {
            "building_id": building_id,
            "unit_number": "101",
            "floor": 1,
            "bedrooms": 2,
            "bathrooms": 1.5,
            "square_feet": 850,
            "monthly_rent": 1500.00,
            "status": "available"
        }
        
        response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["unit_number"] == unit_data["unit_number"]
        assert data["building_id"] == building_id
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_unit_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/units/{id} returns unit details"""
        # Create building and unit
        building_data = {
            "name": "Building for Unit Get",
            "address": "456 Get Unit St",
            "city": "Get City",
            "state": "NY",
            "zip_code": "54321",
            "building_type": "residential",
            "total_units": 5
        }
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = building_response.json()["id"]
        
        unit_data = {
            "building_id": building_id,
            "unit_number": "202",
            "floor": 2,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1200,
            "monthly_rent": 2000.00,
            "status": "occupied"
        }
        
        create_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = create_response.json()["id"]
        
        # Now get it
        response = await client.get(
            f"/api/v1/units/{unit_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == unit_id
        assert data["unit_number"] == unit_data["unit_number"]

    @pytest.mark.asyncio
    async def test_update_unit(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/units/{id} updates unit"""
        # Create building and unit
        building_data = {
            "name": "Building for Unit Update",
            "address": "789 Update St",
            "city": "Update City",
            "state": "TX",
            "zip_code": "78901",
            "building_type": "residential",
            "total_units": 8
        }
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = building_response.json()["id"]
        
        unit_data = {
            "building_id": building_id,
            "unit_number": "303",
            "floor": 3,
            "bedrooms": 1,
            "bathrooms": 1,
            "square_feet": 650,
            "monthly_rent": 1200.00,
            "status": "available"
        }
        
        create_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            **unit_data,
            "monthly_rent": 1300.00,
            "status": "occupied"
        }
        
        response = await client.put(
            f"/api/v1/units/{unit_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_rent"] == 1300.00
        assert data["status"] == "occupied"

    @pytest.mark.asyncio
    async def test_filter_units_by_building(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/units?building_id={id} filters by building"""
        # Create a building
        building_data = {
            "name": "Building for Filter Test",
            "address": "111 Filter St",
            "city": "Filter City",
            "state": "WA",
            "zip_code": "11111",
            "building_type": "residential",
            "total_units": 3
        }
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = building_response.json()["id"]
        
        # Create units in this building
        for i in range(3):
            unit_data = {
                "building_id": building_id,
                "unit_number": f"{i+1}01",
                "floor": i + 1,
                "bedrooms": 2,
                "bathrooms": 1,
                "square_feet": 800,
                "monthly_rent": 1400.00,
                "status": "available"
            }
            await client.post("/api/v1/units", headers=admin_headers, json=unit_data)
        
        # Filter by building
        response = await client.get(
            f"/api/v1/units?building_id={building_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all(unit["building_id"] == building_id for unit in data)
