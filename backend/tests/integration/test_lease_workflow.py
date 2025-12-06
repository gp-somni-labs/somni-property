"""
Integration tests for complete lease workflow
Tests the full lifecycle: Building -> Unit -> Tenant -> Lease -> Payments
"""
import pytest
from httpx import AsyncClient
from datetime import date, timedelta


class TestLeaseWorkflow:
    """Test complete lease lifecycle from building creation to payment"""

    @pytest.mark.asyncio
    async def test_complete_lease_workflow(self, client: AsyncClient, admin_headers):
        """Test complete workflow: Create building, unit, tenant, lease, and payment"""
        
        # Step 1: Create a building
        building_data = {
            "name": "Workflow Test Building",
            "address": "123 Workflow St",
            "city": "Workflow City",
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
        assert building_response.status_code == 201
        building = building_response.json()
        building_id = building["id"]
        
        # Step 2: Create a unit in the building
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
        assert unit_response.status_code == 201
        unit = unit_response.json()
        unit_id = unit["id"]
        
        # Step 3: Create a tenant
        tenant_data = {
            "first_name": "John",
            "last_name": "Workflow",
            "email": "john.workflow@example.com",
            "phone": "555-1111",
            "emergency_contact_name": "Jane Workflow",
            "emergency_contact_phone": "555-2222"
        }
        
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json=tenant_data
        )
        assert tenant_response.status_code == 201
        tenant = tenant_response.json()
        tenant_id = tenant["id"]
        
        # Step 4: Create a lease linking tenant and unit
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
        
        lease_response = await client.post(
            "/api/v1/leases",
            headers=admin_headers,
            json=lease_data
        )
        assert lease_response.status_code == 201
        lease = lease_response.json()
        lease_id = lease["id"]
        
        # Step 5: Update unit status to occupied
        unit_update = {
            **unit_data,
            "status": "occupied"
        }
        
        unit_update_response = await client.put(
            f"/api/v1/units/{unit_id}",
            headers=admin_headers,
            json=unit_update
        )
        assert unit_update_response.status_code == 200
        updated_unit = unit_update_response.json()
        assert updated_unit["status"] == "occupied"
        
        # Step 6: Create first month's payment
        payment_data = {
            "tenant_id": tenant_id,
            "amount": 1500.00,
            "payment_date": date.today().isoformat(),
            "payment_for_month": date.today().strftime("%Y-%m"),
            "payment_method": "credit_card",
            "status": "completed"
        }
        
        payment_response = await client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json=payment_data
        )
        assert payment_response.status_code == 201
        payment = payment_response.json()
        assert payment["amount"] == 1500.00
        assert payment["tenant_id"] == tenant_id
        
        # Step 7: Verify the complete chain exists
        # Get building and verify it has units
        building_check = await client.get(
            f"/api/v1/buildings/{building_id}",
            headers=admin_headers
        )
        assert building_check.status_code == 200
        
        # Get unit and verify it's linked to building
        unit_check = await client.get(
            f"/api/v1/units/{unit_id}",
            headers=admin_headers
        )
        assert unit_check.status_code == 200
        unit_data_check = unit_check.json()
        assert unit_data_check["building_id"] == building_id
        
        # Get lease and verify relationships
        lease_check = await client.get(
            f"/api/v1/leases/{lease_id}",
            headers=admin_headers
        )
        assert lease_check.status_code == 200
        lease_data_check = lease_check.json()
        assert lease_data_check["unit_id"] == unit_id
        assert lease_data_check["tenant_id"] == tenant_id
        
        # Verify payments are linked to tenant
        payments_check = await client.get(
            f"/api/v1/payments?tenant_id={tenant_id}",
            headers=admin_headers
        )
        assert payments_check.status_code == 200
        payments_list = payments_check.json()
        assert len(payments_list) >= 1
        assert any(p["amount"] == 1500.00 for p in payments_list)

    @pytest.mark.asyncio
    async def test_lease_termination_workflow(self, client: AsyncClient, admin_headers):
        """Test workflow for terminating a lease and making unit available"""
        
        # Create building, unit, tenant, and lease
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json={
                "name": "Termination Test Building",
                "address": "456 Term St",
                "city": "Term City",
                "state": "NY",
                "zip_code": "54321",
                "building_type": "residential",
                "total_units": 5
            }
        )
        building_id = building_response.json()["id"]
        
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json={
                "building_id": building_id,
                "unit_number": "202",
                "floor": 2,
                "bedrooms": 1,
                "bathrooms": 1,
                "square_feet": 650,
                "monthly_rent": 1200.00,
                "status": "occupied"
            }
        )
        unit_id = unit_response.json()["id"]
        
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json={
                "first_name": "Jane",
                "last_name": "Termination",
                "email": "jane.term@example.com",
                "phone": "555-3333"
            }
        )
        tenant_id = tenant_response.json()["id"]
        
        lease_response = await client.post(
            "/api/v1/leases",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "tenant_id": tenant_id,
                "start_date": (date.today() - timedelta(days=180)).isoformat(),
                "end_date": (date.today() + timedelta(days=185)).isoformat(),
                "monthly_rent": 1200.00,
                "security_deposit": 1200.00,
                "status": "active"
            }
        )
        lease_id = lease_response.json()["id"]
        
        # Terminate the lease
        terminate_response = await client.put(
            f"/api/v1/leases/{lease_id}",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "tenant_id": tenant_id,
                "start_date": (date.today() - timedelta(days=180)).isoformat(),
                "end_date": date.today().isoformat(),
                "monthly_rent": 1200.00,
                "security_deposit": 1200.00,
                "status": "terminated"
            }
        )
        assert terminate_response.status_code == 200
        terminated_lease = terminate_response.json()
        assert terminated_lease["status"] == "terminated"
        
        # Make unit available again
        make_available_response = await client.put(
            f"/api/v1/units/{unit_id}",
            headers=admin_headers,
            json={
                "building_id": building_id,
                "unit_number": "202",
                "floor": 2,
                "bedrooms": 1,
                "bathrooms": 1,
                "square_feet": 650,
                "monthly_rent": 1200.00,
                "status": "available"
            }
        )
        assert make_available_response.status_code == 200
        available_unit = make_available_response.json()
        assert available_unit["status"] == "available"

    @pytest.mark.asyncio
    async def test_multi_payment_workflow(self, client: AsyncClient, admin_headers):
        """Test workflow with multiple monthly payments"""
        
        # Create tenant
        tenant_response = await client.post(
            "/api/v1/tenants",
            headers=admin_headers,
            json={
                "first_name": "Multi",
                "last_name": "Payment",
                "email": "multi.payment@example.com",
                "phone": "555-4444"
            }
        )
        tenant_id = tenant_response.json()["id"]
        
        # Create 6 months of payments
        months = []
        for i in range(6):
            payment_date = date.today() - timedelta(days=30 * (5 - i))
            payment_month = payment_date.strftime("%Y-%m")
            
            payment_response = await client.post(
                "/api/v1/payments",
                headers=admin_headers,
                json={
                    "tenant_id": tenant_id,
                    "amount": 1500.00,
                    "payment_date": payment_date.isoformat(),
                    "payment_for_month": payment_month,
                    "payment_method": "credit_card",
                    "status": "completed"
                }
            )
            assert payment_response.status_code == 201
            months.append(payment_month)
        
        # Verify all payments exist
        payments_response = await client.get(
            f"/api/v1/payments?tenant_id={tenant_id}",
            headers=admin_headers
        )
        assert payments_response.status_code == 200
        payments = payments_response.json()
        assert len(payments) >= 6
        
        # Verify payment summary
        summary_response = await client.get(
            "/api/v1/payments/summary",
            headers=admin_headers
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert "total_collected" in summary
        assert summary["total_collected"] >= 9000.00  # 6 months * 1500
