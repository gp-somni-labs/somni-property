"""
RBAC System Tests
Tests for Role-Based Access Control permissions matrix and decorators
EPIC K: RBAC Role Matrix + Route Guards
"""

import pytest
from core.security.rbac import (
    Role,
    ROLE_PERMISSIONS,
    has_permission,
    get_all_permissions
)


class TestRolePermissions:
    """Test role permissions matrix"""

    def test_admin_has_all_permissions(self):
        """Admin should have full access to all resources"""
        admin_perms = get_all_permissions(Role.ADMIN)

        # Admin should have permissions on all key resources
        assert "deployments" in admin_perms
        assert "hubs" in admin_perms
        assert "work_orders" in admin_perms
        assert "leases" in admin_perms
        assert "payments" in admin_perms

        # Admin should have all CRUD operations
        assert "create" in admin_perms["deployments"]
        assert "read" in admin_perms["deployments"]
        assert "update" in admin_perms["deployments"]
        assert "delete" in admin_perms["deployments"]

    def test_operator_cannot_delete(self):
        """Operator should not be able to delete critical resources"""
        operator_perms = get_all_permissions(Role.OPERATOR)

        # Operator can create/read/update but not delete
        assert "create" in operator_perms.get("deployments", [])
        assert "read" in operator_perms.get("deployments", [])
        assert "update" in operator_perms.get("deployments", [])
        assert "delete" not in operator_perms.get("deployments", [])

        # Operator can update hubs but not delete
        assert "update" in operator_perms.get("hubs", [])
        assert "delete" not in operator_perms.get("hubs", [])

    def test_technician_limited_access(self):
        """Technician should only access work orders and alerts"""
        tech_perms = get_all_permissions(Role.TECHNICIAN)

        # Technician can read/update work orders
        assert "read" in tech_perms.get("work_orders", [])
        assert "update" in tech_perms.get("work_orders", [])

        # Technician cannot create work orders
        assert "create" not in tech_perms.get("work_orders", [])

        # Technician can acknowledge alerts
        assert "read" in tech_perms.get("alerts", [])
        assert "acknowledge" in tech_perms.get("alerts", [])

        # Technician cannot access payments
        assert "payments" not in tech_perms

    def test_read_only_no_mutations(self):
        """Read-only role should have no write permissions"""
        readonly_perms = get_all_permissions(Role.READ_ONLY)

        # Read-only can read various resources
        assert "read" in readonly_perms.get("deployments", [])
        assert "read" in readonly_perms.get("work_orders", [])
        assert "read" in readonly_perms.get("leases", [])

        # Read-only cannot perform any mutations
        for resource, actions in readonly_perms.items():
            assert "create" not in actions, f"Read-only should not create {resource}"
            assert "update" not in actions, f"Read-only should not update {resource}"
            assert "delete" not in actions, f"Read-only should not delete {resource}"


class TestHasPermission:
    """Test has_permission function"""

    def test_admin_deployment_create(self):
        """Admin should be able to create deployments"""
        assert has_permission(Role.ADMIN, "deployments", "create")

    def test_operator_deployment_create(self):
        """Operator should be able to create deployments"""
        assert has_permission(Role.OPERATOR, "deployments", "create")

    def test_technician_deployment_create(self):
        """Technician should NOT be able to create deployments"""
        assert not has_permission(Role.TECHNICIAN, "deployments", "create")

    def test_read_only_deployment_create(self):
        """Read-only should NOT be able to create deployments"""
        assert not has_permission(Role.READ_ONLY, "deployments", "create")

    def test_technician_work_order_update(self):
        """Technician should be able to update work orders"""
        assert has_permission(Role.TECHNICIAN, "work_orders", "update")

    def test_technician_work_order_delete(self):
        """Technician should NOT be able to delete work orders"""
        assert not has_permission(Role.TECHNICIAN, "work_orders", "delete")

    def test_operator_work_order_assign(self):
        """Operator should be able to assign work orders"""
        assert has_permission(Role.OPERATOR, "work_orders", "assign")

    def test_technician_work_order_assign(self):
        """Technician should NOT be able to assign work orders"""
        assert not has_permission(Role.TECHNICIAN, "work_orders", "assign")

    def test_admin_audit_logs_read(self):
        """Admin should be able to read audit logs"""
        assert has_permission(Role.ADMIN, "audit_logs", "read")

    def test_read_only_audit_logs_read(self):
        """Read-only should be able to read audit logs"""
        assert has_permission(Role.READ_ONLY, "audit_logs", "read")

    def test_operator_system_settings_update(self):
        """Operator should NOT be able to update system settings"""
        assert not has_permission(Role.OPERATOR, "system_settings", "update")

    def test_admin_system_settings_update(self):
        """Admin should be able to update system settings"""
        assert has_permission(Role.ADMIN, "system_settings", "update")


class TestResourceAccess:
    """Test role access to specific resources"""

    def test_payment_access(self):
        """Test payment resource access by role"""
        # Admin has full access
        assert has_permission(Role.ADMIN, "payments", "create")
        assert has_permission(Role.ADMIN, "payments", "read")
        assert has_permission(Role.ADMIN, "payments", "update")
        assert has_permission(Role.ADMIN, "payments", "delete")

        # Operator can only read payments
        assert has_permission(Role.OPERATOR, "payments", "read")
        assert not has_permission(Role.OPERATOR, "payments", "create")
        assert not has_permission(Role.OPERATOR, "payments", "update")
        assert not has_permission(Role.OPERATOR, "payments", "delete")

        # Technician has no payment access
        assert not has_permission(Role.TECHNICIAN, "payments", "read")

        # Read-only can view payments
        assert has_permission(Role.READ_ONLY, "payments", "read")
        assert not has_permission(Role.READ_ONLY, "payments", "create")

    def test_lease_access(self):
        """Test lease resource access by role"""
        # Admin has full access
        assert has_permission(Role.ADMIN, "leases", "create")
        assert has_permission(Role.ADMIN, "leases", "delete")

        # Operator can read/update but not create/delete
        assert has_permission(Role.OPERATOR, "leases", "read")
        assert has_permission(Role.OPERATOR, "leases", "update")
        assert not has_permission(Role.OPERATOR, "leases", "create")
        assert not has_permission(Role.OPERATOR, "leases", "delete")

        # Technician has no lease access
        assert not has_permission(Role.TECHNICIAN, "leases", "read")

        # Read-only can view leases
        assert has_permission(Role.READ_ONLY, "leases", "read")

    def test_contractor_access(self):
        """Test contractor resource access by role"""
        # Admin has full access
        assert has_permission(Role.ADMIN, "contractors", "create")
        assert has_permission(Role.ADMIN, "contractors", "delete")

        # Operator can read/update contractors
        assert has_permission(Role.OPERATOR, "contractors", "read")
        assert has_permission(Role.OPERATOR, "contractors", "update")
        assert not has_permission(Role.OPERATOR, "contractors", "create")
        assert not has_permission(Role.OPERATOR, "contractors", "delete")

        # Technician can only read contractors
        assert has_permission(Role.TECHNICIAN, "contractors", "read")
        assert not has_permission(Role.TECHNICIAN, "contractors", "update")

    def test_alert_access(self):
        """Test alert resource access by role"""
        # Admin has full access including resolve
        assert has_permission(Role.ADMIN, "alerts", "read")
        assert has_permission(Role.ADMIN, "alerts", "acknowledge")
        assert has_permission(Role.ADMIN, "alerts", "resolve")

        # Operator can acknowledge and resolve
        assert has_permission(Role.OPERATOR, "alerts", "acknowledge")
        assert has_permission(Role.OPERATOR, "alerts", "resolve")

        # Technician can only read and acknowledge
        assert has_permission(Role.TECHNICIAN, "alerts", "read")
        assert has_permission(Role.TECHNICIAN, "alerts", "acknowledge")
        assert not has_permission(Role.TECHNICIAN, "alerts", "resolve")

        # Read-only can only view alerts
        assert has_permission(Role.READ_ONLY, "alerts", "read")
        assert not has_permission(Role.READ_ONLY, "alerts", "acknowledge")


class TestRoleEnum:
    """Test Role enum"""

    def test_all_roles_defined(self):
        """All expected roles should be defined"""
        expected_roles = {"admin", "operator", "technician", "read_only"}
        actual_roles = {role.value for role in Role}
        assert actual_roles == expected_roles

    def test_role_string_values(self):
        """Role values should be lowercase strings"""
        assert Role.ADMIN.value == "admin"
        assert Role.OPERATOR.value == "operator"
        assert Role.TECHNICIAN.value == "technician"
        assert Role.READ_ONLY.value == "read_only"


class TestPermissionMatrix:
    """Test the complete permission matrix"""

    def test_all_roles_have_permissions(self):
        """Every role should have at least one permission"""
        for role in Role:
            perms = get_all_permissions(role)
            assert len(perms) > 0, f"Role {role.value} has no permissions"

    def test_admin_most_permissive(self):
        """Admin should have more permissions than any other role"""
        admin_perms = get_all_permissions(Role.ADMIN)
        admin_count = sum(len(actions) for actions in admin_perms.values())

        for role in [Role.OPERATOR, Role.TECHNICIAN, Role.READ_ONLY]:
            role_perms = get_all_permissions(role)
            role_count = sum(len(actions) for actions in role_perms.values())
            assert admin_count > role_count, f"Admin should have more permissions than {role.value}"

    def test_read_only_least_permissive(self):
        """Read-only should have fewer permissions than any other role"""
        readonly_perms = get_all_permissions(Role.READ_ONLY)
        readonly_count = sum(len(actions) for actions in readonly_perms.values())

        for role in [Role.ADMIN, Role.OPERATOR, Role.TECHNICIAN]:
            role_perms = get_all_permissions(role)
            role_count = sum(len(actions) for actions in role_perms.values())
            assert readonly_count < role_count, f"Read-only should have fewer permissions than {role.value}"

    def test_no_invalid_actions(self):
        """All actions should be valid CRUD or special operations"""
        valid_actions = {
            "create", "read", "update", "delete",
            "assign", "acknowledge", "resolve"
        }

        for role in Role:
            perms = get_all_permissions(role)
            for resource, actions in perms.items():
                for action in actions:
                    assert action in valid_actions, \
                        f"Invalid action '{action}' for {role.value} on {resource}"


# Integration test helpers (to be used with FastAPI TestClient)
class TestRBACDecorators:
    """
    These are example test cases for RBAC decorators.
    Actual implementation would use FastAPI TestClient to test endpoints.
    """

    def test_example_structure(self):
        """
        Example of how to test RBAC decorators with endpoints:

        @pytest.mark.asyncio
        async def test_deployment_create_requires_permission():
            # Create test client with admin headers
            headers = {"X-User-Role": "admin"}
            response = client.post("/api/v1/fleet/deploy", headers=headers, json={...})
            assert response.status_code == 200

            # Try with read-only role
            headers = {"X-User-Role": "read_only"}
            response = client.post("/api/v1/fleet/deploy", headers=headers, json={...})
            assert response.status_code == 403
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
