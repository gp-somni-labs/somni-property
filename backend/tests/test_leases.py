"""
Leases API Tests
Tests for lease CRUD operations and business logic
"""

import pytest
from httpx import AsyncClient
from datetime import date, timedelta


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_lease(client: AsyncClient, manager_headers, sample_unit, sample_tenant):
    """Test creating a new lease"""
    lease_data = {
        "unit_id": str(sample_unit.id),
        "tenant_id": str(sample_tenant.id),
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
        "monthly_rent": 1500.00,
        "security_deposit": 1500.00,
        "status": "active"
    }

    response = await client.post(
        "/api/v1/leases",
        json=lease_data,
        headers=manager_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert float(data["monthly_rent"]) == 1500.00
    assert data["status"] == "active"


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_leases_as_manager(client: AsyncClient, manager_headers, sample_lease):
    """Test that managers can list all leases"""
    response = await client.get("/api/v1/leases", headers=manager_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.api
@pytest.mark.asyncio
async def test_tenant_can_view_own_leases(client: AsyncClient, tenant_headers, sample_lease):
    """Test that tenant can view their own leases"""
    response = await client.get("/api/v1/leases", headers=tenant_headers)

    assert response.status_code == 200
    data = response.json()
    # Should only see their own leases
    assert all(item["tenant_id"] == str(sample_lease.tenant_id) for item in data["items"])


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_overlapping_lease_fails(client: AsyncClient, manager_headers, sample_lease):
    """Test that creating overlapping leases fails"""
    overlapping_data = {
        "unit_id": str(sample_lease.unit_id),
        "tenant_id": str(sample_lease.tenant_id),
        "start_date": str(date.today() + timedelta(days=30)),  # Overlaps with existing lease
        "end_date": str(date.today() + timedelta(days=395)),
        "monthly_rent": 1500.00,
        "security_deposit": 1500.00,
        "status": "active"
    }

    response = await client.post(
        "/api/v1/leases",
        json=overlapping_data,
        headers=manager_headers
    )

    assert response.status_code == 409  # Conflict
    assert "already has an active lease" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_renew_lease(client: AsyncClient, manager_headers, sample_lease):
    """Test renewing a lease"""
    new_end_date = date.today() + timedelta(days=730)  # 2 years from now

    response = await client.post(
        f"/api/v1/leases/{sample_lease.id}/renew",
        params={"new_end_date": str(new_end_date)},
        headers=manager_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    # Original lease should be different from renewed lease
    assert data["id"] != str(sample_lease.id)


@pytest.mark.api
@pytest.mark.asyncio
async def test_terminate_lease(client: AsyncClient, manager_headers, sample_lease):
    """Test terminating a lease"""
    termination_date = date.today() + timedelta(days=30)

    response = await client.post(
        f"/api/v1/leases/{sample_lease.id}/terminate",
        params={"termination_date": str(termination_date)},
        headers=manager_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "terminated"


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_expiring_leases(client: AsyncClient, manager_headers):
    """Test getting leases expiring soon"""
    response = await client.get(
        "/api/v1/leases/expiring-soon",
        params={"days": 60},
        headers=manager_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
