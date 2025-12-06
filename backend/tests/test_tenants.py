"""
Tenants API Tests
Tests for tenant CRUD operations and access control
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_tenant(client: AsyncClient, manager_headers):
    """Test creating a new tenant"""
    tenant_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "503-555-0199",
        "status": "applicant"
    }

    response = await client.post(
        "/api/v1/tenants",
        json=tenant_data,
        headers=manager_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"
    assert data["email"] == "jane.smith@example.com"


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_tenants_as_manager(client: AsyncClient, manager_headers, sample_tenant):
    """Test that managers can list all tenants"""
    response = await client.get("/api/v1/tenants", headers=manager_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_tenants_as_tenant_fails(client: AsyncClient, tenant_headers):
    """Test that tenants cannot list all tenants"""
    response = await client.get("/api/v1/tenants", headers=tenant_headers)

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.asyncio
async def test_tenant_can_view_own_profile(client: AsyncClient, sample_tenant, tenant_headers):
    """Test that tenant can view their own profile"""
    response = await client.get("/api/v1/tenants/me", headers=tenant_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "john.doe@example.com"


@pytest.mark.api
@pytest.mark.asyncio
async def test_tenant_can_update_own_profile(client: AsyncClient, sample_tenant, tenant_headers):
    """Test that tenant can update their own profile"""
    update_data = {
        "phone": "503-555-9999"
    }

    response = await client.put(
        "/api/v1/tenants/me",
        json=update_data,
        headers=tenant_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "503-555-9999"


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_duplicate_email_fails(client: AsyncClient, manager_headers, sample_tenant):
    """Test that creating a tenant with duplicate email fails"""
    duplicate_data = {
        "first_name": "Another",
        "last_name": "Person",
        "email": sample_tenant.email,  # Duplicate email
        "status": "applicant"
    }

    response = await client.post(
        "/api/v1/tenants",
        json=duplicate_data,
        headers=manager_headers
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
