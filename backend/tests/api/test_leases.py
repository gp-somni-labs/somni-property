"""
Tests for Leases API endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import date, timedelta


class TestLeasesAPI:
    """Test Leases CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_leases(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/leases returns list of leases"""
        response = await client.get("/api/v1/leases", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_leases_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/leases requires authentication"""
        response = await client.get("/api/v1/leases")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_lease(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/leases creates a new lease"""
        # Create building, unit, and tenant first
        building_data = {
            "name": "Lease Test Building",
            "address": "123 Lease St",
            "city": "Lease City",
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
            "status": "available"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        tenant_data = {
            "first_name": "Lease",
            "last_name": "Holder",
            "email": "lease.holder@example.com",
            "phone": "555-1000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        # Create lease
        start_date = date.today()
        end_date = start_date + timedelta(days=365)
        
        lease_data = {
            "unit_id": unit_id,
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "monthly_rent": 1500.00,
            "security_deposit": 1500.00,
            "status": "active"
        }
        
        response = await client.post(
            "/api/v1/leases",
            headers=admin_headers,
            json=lease_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["unit_id"] == unit_id
        assert data["tenant_id"] == tenant_id
        assert data["monthly_rent"] == 1500.00
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_lease_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/leases/{id} returns lease details"""
        # Create all dependencies and lease
        building_data = {
            "name": "Get Lease Building",
            "address": "456 Get Lease St",
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
            "status": "available"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        tenant_data = {
            "first_name": "Get",
            "last_name": "Lease",
            "email": "get.lease@example.com",
            "phone": "555-2000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        lease_data = {
            "unit_id": unit_id,
            "tenant_id": tenant_id,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat(),
            "monthly_rent": 1200.00,
            "security_deposit": 1200.00,
            "status": "active"
        }
        
        create_response = await client.post(
            "/api/v1/leases",
            headers=admin_headers,
            json=lease_data
        )
        lease_id = create_response.json()["id"]
        
        # Get the lease
        response = await client.get(
            f"/api/v1/leases/{lease_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lease_id
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_update_lease_status(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/leases/{id} updates lease status"""
        # Create dependencies and lease
        building_data = {
            "name": "Update Lease Building",
            "address": "789 Update St",
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
            "status": "available"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        tenant_data = {
            "first_name": "Update",
            "last_name": "Lease",
            "email": "update.lease@example.com",
            "phone": "555-3000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        lease_data = {
            "unit_id": unit_id,
            "tenant_id": tenant_id,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=365)).isoformat(),
            "monthly_rent": 1800.00,
            "security_deposit": 1800.00,
            "status": "active"
        }
        
        create_response = await client.post(
            "/api/v1/leases",
            headers=admin_headers,
            json=lease_data
        )
        lease_id = create_response.json()["id"]
        
        # Update to terminated
        update_data = {
            **lease_data,
            "status": "terminated"
        }
        
        response = await client.put(
            f"/api/v1/leases/{lease_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "terminated"

    @pytest.mark.asyncio
    async def test_filter_leases_by_unit(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/leases?unit_id={id} filters by unit"""
        # Create building and unit
        building_data = {
            "name": "Filter Lease Building",
            "address": "111 Filter St",
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
            "status": "available"
        }
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json=unit_data
        )
        unit_id = unit_response.json()["id"]
        
        # Filter by unit
        response = await client.get(
            f"/api/v1/leases?unit_id={unit_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(lease["unit_id"] == unit_id for lease in data)
