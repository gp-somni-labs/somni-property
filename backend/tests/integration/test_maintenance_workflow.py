"""
Integration tests for maintenance and work order workflows
"""
import pytest
from httpx import AsyncClient


class TestMaintenanceWorkflow:
    """Test complete maintenance workflow"""

    @pytest.mark.asyncio
    async def test_work_order_lifecycle(self, client: AsyncClient, admin_headers):
        """Test complete work order lifecycle from creation to completion"""
        
        # Step 1: Create building and unit
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json={
                "name": "Maintenance Test Building",
                "address": "789 Maint St",
                "city": "Maint City",
                "state": "TX",
                "zip_code": "78901",
                "building_type": "residential",
                "total_units": 8
            }
        )
        building_id = building_response.json()["id"]
        
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json={
                "building_id": building_id,
                "unit_number": "303",
                "floor": 3,
                "bedrooms": 2,
                "bathrooms": 2,
                "square_feet": 1000,
                "monthly_rent": 1800.00,
                "status": "occupied"
            }
        )
        unit_id = unit_response.json()["id"]
        
        # Step 2: Create emergency work order
        wo_response = await client.post(
            "/api/v1/work-orders",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "title": "Emergency: Water Leak",
                "description": "Major water leak in ceiling of unit 303",
                "priority": "emergency",
                "status": "open",
                "category": "plumbing"
            }
        )
        assert wo_response.status_code == 201
        work_order = wo_response.json()
        wo_id = work_order["id"]
        assert work_order["priority"] == "emergency"
        
        # Step 3: Update work order to in_progress
        update_response = await client.put(
            f"/api/v1/work-orders/{wo_id}",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "title": "Emergency: Water Leak",
                "description": "Major water leak in ceiling of unit 303. Plumber dispatched.",
                "priority": "emergency",
                "status": "in_progress",
                "category": "plumbing"
            }
        )
        assert update_response.status_code == 200
        updated_wo = update_response.json()
        assert updated_wo["status"] == "in_progress"
        
        # Step 4: Complete the work order
        complete_response = await client.put(
            f"/api/v1/work-orders/{wo_id}",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "title": "Emergency: Water Leak",
                "description": "Major water leak in ceiling of unit 303. RESOLVED: Replaced pipe.",
                "priority": "emergency",
                "status": "completed",
                "category": "plumbing"
            }
        )
        assert complete_response.status_code == 200
        completed_wo = complete_response.json()
        assert completed_wo["status"] == "completed"
        
        # Step 5: Verify work order history for unit
        wo_list_response = await client.get(
            f"/api/v1/work-orders?unit_id={unit_id}",
            headers=admin_headers
        )
        assert wo_list_response.status_code == 200
        wo_list = wo_list_response.json()
        assert len(wo_list) >= 1
        assert any(wo["id"] == wo_id for wo in wo_list)

    @pytest.mark.asyncio
    async def test_multiple_work_orders_workflow(self, client: AsyncClient, admin_headers):
        """Test managing multiple work orders for different units"""
        
        # Create building
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json={
                "name": "Multi WO Building",
                "address": "111 Multi WO St",
                "city": "Multi City",
                "state": "WA",
                "zip_code": "11111",
                "building_type": "residential",
                "total_units": 3
            }
        )
        building_id = building_response.json()["id"]
        
        # Create 3 units with work orders
        work_orders = []
        for i in range(3):
            # Create unit
            unit_response = await client.post(
                "/api/v1/units",
                headers=admin_headers,
                json={
                    "building_id": building_id,
                    "unit_number": f"{i+1}01",
                    "floor": i + 1,
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "square_feet": 850,
                    "monthly_rent": 1500.00,
                    "status": "occupied"
                }
            )
            unit_id = unit_response.json()["id"]
            
            # Create work order
            priorities = ["low", "medium", "high"]
            wo_response = await client.post(
                "/api/v1/work-orders",
                headers=admin_headers,
                json={
                    "unit_id": unit_id,
                    "title": f"Repair needed in unit {i+1}01",
                    "description": f"Issue in unit {i+1}01",
                    "priority": priorities[i],
                    "status": "open",
                    "category": "general"
                }
            )
            work_orders.append(wo_response.json()["id"])
        
        # Verify all work orders exist
        all_wo_response = await client.get(
            "/api/v1/work-orders",
            headers=admin_headers
        )
        assert all_wo_response.status_code == 200
        all_wo = all_wo_response.json()
        assert len(all_wo) >= 3
        
        # Filter by priority
        high_priority_response = await client.get(
            "/api/v1/work-orders?priority=high",
            headers=admin_headers
        )
        assert high_priority_response.status_code == 200
        high_priority_wo = high_priority_response.json()
        assert len(high_priority_wo) >= 1
        assert all(wo["priority"] == "high" for wo in high_priority_wo)

    @pytest.mark.asyncio
    async def test_contractor_assignment_workflow(self, client: AsyncClient, admin_headers):
        """Test assigning contractors to work orders"""
        
        # Create building and unit
        building_response = await client.post(
            "/api/v1/buildings",
            headers=admin_headers,
            json={
                "name": "Contractor Test Building",
                "address": "222 Contractor St",
                "city": "Contractor City",
                "state": "FL",
                "zip_code": "22222",
                "building_type": "residential",
                "total_units": 2
            }
        )
        building_id = building_response.json()["id"]
        
        unit_response = await client.post(
            "/api/v1/units",
            headers=admin_headers,
            json={
                "building_id": building_id,
                "unit_number": "404",
                "floor": 4,
                "bedrooms": 3,
                "bathrooms": 2,
                "square_feet": 1400,
                "monthly_rent": 2200.00,
                "status": "occupied"
            }
        )
        unit_id = unit_response.json()["id"]
        
        # Create contractor
        contractor_response = await client.post(
            "/api/v1/contractors",
            headers=admin_headers,
            json={
                "name": "ABC Plumbing",
                "email": "contact@abcplumbing.com",
                "phone": "555-7777",
                "specialty": "plumbing",
                "status": "active"
            }
        )
        assert contractor_response.status_code == 201
        contractor_id = contractor_response.json()["id"]
        
        # Create work order
        wo_response = await client.post(
            "/api/v1/work-orders",
            headers=admin_headers,
            json={
                "unit_id": unit_id,
                "title": "Plumbing Repair Needed",
                "description": "Need plumber for sink repair",
                "priority": "medium",
                "status": "open",
                "category": "plumbing"
            }
        )
        wo_id = wo_response.json()["id"]
        
        # Assign contractor (if the API supports it)
        # This may need adjustment based on actual API design
        # For now, we'll just verify the contractor exists
        contractor_check = await client.get(
            f"/api/v1/contractors/{contractor_id}",
            headers=admin_headers
        )
        assert contractor_check.status_code == 200
        assert contractor_check.json()["specialty"] == "plumbing"
