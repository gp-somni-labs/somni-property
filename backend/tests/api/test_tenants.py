"""
Tests for Tenants API endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestTenantsAPI:
    """Test Tenants CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_tenants(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/tenants returns list of tenants"""
        response = await client.get("/api/v1/tenants", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_tenants_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/tenants requires authentication"""
        response = await client.get("/api/v1/tenants")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_tenant(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/tenants creates a new tenant"""
        tenant_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-0100",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "555-0101"
        }
        
        response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == tenant_data["first_name"]
        assert data["last_name"] == tenant_data["last_name"]
        assert data["email"] == tenant_data["email"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_tenant_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/tenants/{id} returns tenant details"""
        # Create a tenant
        tenant_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "phone": "555-0200",
            "emergency_contact_name": "John Smith",
            "emergency_contact_phone": "555-0201"
        }
        
        create_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = create_response.json()["id"]
        
        # Get it
        response = await client.get(
            f"/api/v1/tenants/{tenant_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_id
        assert data["email"] == tenant_data["email"]

    @pytest.mark.asyncio
    async def test_update_tenant(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/tenants/{id} updates tenant"""
        # Create a tenant
        tenant_data = {
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob.johnson@example.com",
            "phone": "555-0300"
        }
        
        create_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            **tenant_data,
            "phone": "555-9999",
            "email": "bob.j.updated@example.com"
        }
        
        response = await client.put(
            f"/api/v1/tenants/{tenant_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "555-9999"
        assert data["email"] == "bob.j.updated@example.com"

    @pytest.mark.asyncio
    async def test_delete_tenant(self, client: AsyncClient, admin_headers):
        """Test DELETE /api/v1/tenants/{id} deletes tenant"""
        # Create a tenant
        tenant_data = {
            "first_name": "Delete",
            "last_name": "Me",
            "email": "delete.me@example.com",
            "phone": "555-0400"
        }
        
        create_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(
            f"/api/v1/tenants/{tenant_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_search_tenants_by_email(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/tenants?email={email} searches by email"""
        # Create a tenant with unique email
        unique_email = f"search.test.{uuid4().hex[:8]}@example.com"
        tenant_data = {
            "first_name": "Search",
            "last_name": "Test",
            "email": unique_email,
            "phone": "555-0500"
        }
        
        await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        
        # Search for it
        response = await client.get(
            f"/api/v1/tenants?email={unique_email}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(t["email"] == unique_email for t in data)
