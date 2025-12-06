"""
Tests for Payments API endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import date


class TestPaymentsAPI:
    """Test Payments CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_payments(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/payments returns list of payments"""
        response = await client.get("/api/v1/payments", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_payments_unauthorized(self, client: AsyncClient):
        """Test GET /api/v1/payments requires authentication"""
        response = await client.get("/api/v1/payments")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_payment_summary(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/payments/summary returns payment statistics"""
        response = await client.get("/api/v1/payments/summary", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_collected" in data
        assert "total_pending" in data
        assert "total_overdue" in data

    @pytest.mark.asyncio
    async def test_create_payment(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/payments creates a new payment"""
        # Create tenant first
        tenant_data = {
            "first_name": "Payment",
            "last_name": "Tenant",
            "email": "payment.tenant@example.com",
            "phone": "555-5000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        # Create payment
        payment_data = {
            "tenant_id": tenant_id,
            "amount": 1500.00,
            "payment_date": date.today().isoformat(),
            "payment_for_month": date.today().strftime("%Y-%m"),
            "payment_method": "credit_card",
            "status": "completed"
        }
        
        response = await client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json=payment_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == tenant_id
        assert data["amount"] == 1500.00
        assert data["status"] == "completed"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_payment_by_id(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/payments/{id} returns payment details"""
        # Create tenant and payment
        tenant_data = {
            "first_name": "Get",
            "last_name": "Payment",
            "email": "get.payment@example.com",
            "phone": "555-6000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        payment_data = {
            "tenant_id": tenant_id,
            "amount": 1200.00,
            "payment_date": date.today().isoformat(),
            "payment_for_month": date.today().strftime("%Y-%m"),
            "payment_method": "bank_transfer",
            "status": "pending"
        }
        
        create_response = await client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json=payment_data
        )
        payment_id = create_response.json()["id"]
        
        # Get payment
        response = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == payment_id
        assert data["amount"] == 1200.00

    @pytest.mark.asyncio
    async def test_update_payment_status(self, client: AsyncClient, admin_headers):
        """Test PUT /api/v1/payments/{id} updates payment status"""
        # Create tenant and payment
        tenant_data = {
            "first_name": "Update",
            "last_name": "Payment",
            "email": "update.payment@example.com",
            "phone": "555-7000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        payment_data = {
            "tenant_id": tenant_id,
            "amount": 1600.00,
            "payment_date": date.today().isoformat(),
            "payment_for_month": date.today().strftime("%Y-%m"),
            "payment_method": "check",
            "status": "pending"
        }
        
        create_response = await client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json=payment_data
        )
        payment_id = create_response.json()["id"]
        
        # Update to completed
        update_data = {
            **payment_data,
            "status": "completed"
        }
        
        response = await client.put(
            f"/api/v1/payments/{payment_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_filter_payments_by_tenant(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/payments?tenant_id={id} filters by tenant"""
        # Create tenant
        tenant_data = {
            "first_name": "Filter",
            "last_name": "Payments",
            "email": "filter.payments@example.com",
            "phone": "555-8000"
        }
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        tenant_id = tenant_response.json()["id"]
        
        # Create multiple payments for this tenant
        for i in range(3):
            payment_data = {
                "tenant_id": tenant_id,
                "amount": 1500.00 + (i * 100),
                "payment_date": date.today().isoformat(),
                "payment_for_month": date.today().strftime("%Y-%m"),
                "payment_method": "credit_card",
                "status": "completed"
            }
            await client.post("/api/v1/payments", headers=admin_headers, json=payment_data)
        
        # Filter by tenant
        response = await client.get(
            f"/api/v1/payments?tenant_id={tenant_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all(payment["tenant_id"] == tenant_id for payment in data)
