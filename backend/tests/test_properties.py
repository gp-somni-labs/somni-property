"""
Properties API Tests
Tests for property CRUD operations
"""

import pytest
from httpx import AsyncClient
from db.models import Property


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_properties_empty(client: AsyncClient, admin_headers):
    """Test listing properties when none exist"""
    response = await client.get("/api/v1/properties", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.api
@pytest.mark.asyncio
async def test_list_properties_with_data(client: AsyncClient, admin_headers, sample_property):
    """Test listing properties with existing data"""
    response = await client.get("/api/v1/properties", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Oak Street Apartments"


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_property(client: AsyncClient, admin_headers):
    """Test creating a new property"""
    property_data = {
        "name": "Maple Terrace",
        "address_line1": "456 Maple Ave",
        "city": "Portland",
        "state": "OR",
        "zip_code": "97202",
        "property_type": "residential"
    }

    response = await client.post(
        "/api/v1/properties",
        json=property_data,
        headers=admin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Maple Terrace"
    assert data["city"] == "Portland"
    assert "id" in data


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_property_by_id(client: AsyncClient, admin_headers, sample_property):
    """Test getting a property by ID"""
    response = await client.get(
        f"/api/v1/properties/{sample_property.id}",
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Oak Street Apartments"
    assert str(data["id"]) == str(sample_property.id)


@pytest.mark.api
@pytest.mark.asyncio
async def test_update_property(client: AsyncClient, admin_headers, sample_property):
    """Test updating a property"""
    update_data = {
        "current_value": 500000.00
    }

    response = await client.put(
        f"/api/v1/properties/{sample_property.id}",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert float(data["current_value"]) == 500000.00


@pytest.mark.api
@pytest.mark.asyncio
async def test_delete_property(client: AsyncClient, admin_headers, sample_property):
    """Test deleting a property"""
    response = await client.delete(
        f"/api/v1/properties/{sample_property.id}",
        headers=admin_headers
    )

    assert response.status_code == 204

    # Verify property is deleted
    get_response = await client.get(
        f"/api/v1/properties/{sample_property.id}",
        headers=admin_headers
    )
    assert get_response.status_code == 404


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_property_invalid_data(client: AsyncClient, admin_headers):
    """Test creating property with invalid data"""
    invalid_data = {
        "name": "Test Property",
        # Missing required fields
    }

    response = await client.post(
        "/api/v1/properties",
        json=invalid_data,
        headers=admin_headers
    )

    assert response.status_code == 422  # Validation error
