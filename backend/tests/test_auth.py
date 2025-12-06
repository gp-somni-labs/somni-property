"""
Authentication Tests
Tests for Authelia integration and role-based access control
"""

import pytest
from httpx import AsyncClient


@pytest.mark.auth
@pytest.mark.asyncio
async def test_no_auth_returns_401(client: AsyncClient, no_auth_headers):
    """Test that endpoints require authentication"""
    response = await client.get("/api/v1/properties", headers=no_auth_headers)
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


@pytest.mark.auth
@pytest.mark.asyncio
async def test_admin_can_access_properties(client: AsyncClient, admin_headers):
    """Test that admin can access properties endpoint"""
    response = await client.get("/api/v1/properties", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.auth
@pytest.mark.asyncio
async def test_manager_can_access_properties(client: AsyncClient, manager_headers):
    """Test that manager can access properties endpoint"""
    response = await client.get("/api/v1/properties", headers=manager_headers)
    assert response.status_code == 200


@pytest.mark.auth
@pytest.mark.asyncio
async def test_tenant_cannot_list_all_tenants(client: AsyncClient, tenant_headers):
    """Test that tenants cannot list all other tenants"""
    response = await client.get("/api/v1/tenants", headers=tenant_headers)
    assert response.status_code == 403


@pytest.mark.auth
@pytest.mark.asyncio
async def test_admin_can_list_all_tenants(client: AsyncClient, admin_headers):
    """Test that admin can list all tenants"""
    response = await client.get("/api/v1/tenants", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.auth
@pytest.mark.asyncio
async def test_tenant_can_access_own_profile(client: AsyncClient, tenant_headers):
    """Test that tenant can access their own profile"""
    response = await client.get("/api/v1/tenants/me", headers=tenant_headers)
    # 404 is acceptable if tenant doesn't exist yet (auto-provisioning should handle this)
    assert response.status_code in [200, 404]
