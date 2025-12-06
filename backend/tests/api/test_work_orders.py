"""
Tests for Work Orders API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestWorkOrdersAPI:
    """Test Work Orders CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_work_orders(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/work-orders returns list of work orders"""
        response = await client.get("/api/v1/work-orders", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_work_orders_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/work-orders requires authentication"""
        response = await client.get("/api/v1/work-orders")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_work_order(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/work-orders creates a new work order"""
        # Create building and unit first
        building_data = {
            "name": "Work Order Building",
            "address": "123 WO St",
            "city": "WO City",
            "state": "CA",
            "zip_code": "12345",
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
            "unit_number": "101",
            "floor": 1,
            "bedrooms": 2,
            "bathrooms": 1,
            "square_feet": 850,
            "monthly_rent": 1500.00,
            "status": "occupied"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        # Create work order
        work_order_data = {
            "unit_id": unit_id,
            "title": "Leaky Faucet Repair",
            "description": "Kitchen faucet is dripping constantly",
            "priority": "medium",
            "status": "open",
            "category": "plumbing"
        }
        
        response = await client.post(
            "/api/v1/work-orders",
            headers=admin_headers,
            json=work_order_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == work_order_data["title"]
        assert data["unit_id"] == unit_id
        assert data["priority"] == "medium"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_work_order_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/work-orders/{id} returns work order details"""
        # Create building, unit, and work order
        building_data = {
            "name": "Get WO Building",
            "address": "456 Get WO St",
            "city": "Get City",
            "state": "NY",
            "zip_code": "54321",
            "building_type": "residential",
            "total_units": 3
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
            "bedrooms": 1,
            "bathrooms": 1,
            "square_feet": 650,
            "monthly_rent": 1200.00,
            "status": "occupied"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        work_order_data = {
            "unit_id": unit_id,
            "title": "AC Not Working",
            "description": "Air conditioning unit is not turning on",
            "priority": "high",
            "status": "open",
            "category": "hvac"
        }
        
        create_response = await client.post(
            "/api/v1/work-orders",
            headers=admin_headers,
            json=work_order_data
        )
        work_order_id = create_response.json()["id"]
        
        # Get work order
        response = await client.get(
            f"/api/v1/work-orders/{work_order_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == work_order_id
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_update_work_order_status(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/work-orders/{id} updates work order status"""
        # Create building, unit, and work order
        building_data = {
            "name": "Update WO Building",
            "address": "789 Update WO St",
            "city": "Update City",
            "state": "TX",
            "zip_code": "78901",
            "building_type": "residential",
            "total_units": 2
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
            "bedrooms": 2,
            "bathrooms": 2,
            "square_feet": 1000,
            "monthly_rent": 1800.00,
            "status": "occupied"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        work_order_data = {
            "unit_id": unit_id,
            "title": "Light Bulb Replacement",
            "description": "Replace hallway light bulbs",
            "priority": "low",
            "status": "open",
            "category": "electrical"
        }
        
        create_response = await client.post(
            "/api/v1/work-orders",
            headers=admin_headers,
            json=work_order_data
        )
        work_order_id = create_response.json()["id"]
        
        # Update to in_progress
        update_data = {
            **work_order_data,
            "status": "in_progress"
        }
        
        response = await client.put(
            f"/api/v1/work-orders/{work_order_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        
        # Update to completed
        update_data["status"] = "completed"
        response = await client.put(
            f"/api/v1/work-orders/{work_order_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_filter_work_orders_by_priority(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/work-orders?priority={priority} filters by priority"""
        # Create building and unit
        building_data = {
            "name": "Filter WO Building",
            "address": "111 Filter WO St",
            "city": "Filter City",
            "state": "WA",
            "zip_code": "11111",
            "building_type": "residential",
            "total_units": 1
        }
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json=building_data
        )
        building_id = building_response.json()["id"]
        
        unit_data = {
            "building_id": building_id,
            "unit_number": "404",
            "floor": 4,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1400,
            "monthly_rent": 2200.00,
            "status": "occupied"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        # Create emergency work order
        emergency_wo = {
            "unit_id": unit_id,
            "title": "Emergency: Water Leak",
            "description": "Major water leak in ceiling",
            "priority": "emergency",
            "status": "open",
            "category": "plumbing"
        }
        await client.post("/api/v1/work-orders", headers=admin_headers, json=emergency_wo)
        
        # Filter by emergency priority
        response = await client.get(
            "/api/v1/work-orders?priority=emergency",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(wo["priority"] == "emergency" for wo in data)

    @pytest.mark.asyncio
    async def test_filter_work_orders_by_status(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/work-orders?status={status} filters by status"""
        response = await client.get(
            "/api/v1/work-orders?status=open",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(wo["status"] == "open" for wo in data)
