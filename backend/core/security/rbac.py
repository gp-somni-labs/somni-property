"""
RBAC (Role-Based Access Control) System
Defines roles, permissions, and decorators for endpoint access control
"""

from enum import Enum
from typing import List, Set, Optional
from fastapi import HTTPException, Request, Depends
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    OPERATOR = "operator"
    TECHNICIAN = "technician"
    READ_ONLY = "read_only"


# Role permissions matrix
# Defines what actions each role can perform on each resource
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        # Full access to all resources
        "deployments": ["create", "read", "update", "delete"],
        "hubs": ["create", "read", "update", "delete"],
        "work_orders": ["create", "read", "update", "delete", "assign"],
        "contractors": ["create", "read", "update", "delete"],
        "alerts": ["create", "read", "update", "delete", "acknowledge", "resolve"],
        "tenants": ["create", "read", "update", "delete"],
        "leases": ["create", "read", "update", "delete"],
        "payments": ["create", "read", "update", "delete"],
        "clients": ["create", "read", "update", "delete"],
        "buildings": ["create", "read", "update", "delete"],
        "units": ["create", "read", "update", "delete"],
        "properties": ["create", "read", "update", "delete"],
        "service_packages": ["create", "read", "update", "delete"],
        "service_contracts": ["create", "read", "update", "delete"],
        "documents": ["create", "read", "update", "delete"],
        "audit_logs": ["read"],
        "system_settings": ["read", "update"]
    },
    Role.OPERATOR: {
        # Operations staff - can manage most resources but not delete critical ones
        "deployments": ["create", "read", "update"],
        "hubs": ["read", "update"],
        "work_orders": ["create", "read", "update", "assign"],
        "contractors": ["read", "update"],
        "alerts": ["read", "acknowledge", "resolve"],
        "tenants": ["read", "update"],
        "leases": ["read", "update"],
        "payments": ["read"],
        "clients": ["read", "update"],
        "buildings": ["read", "update"],
        "units": ["read", "update"],
        "properties": ["read", "update"],
        "service_packages": ["read"],
        "service_contracts": ["read", "update"],
        "documents": ["create", "read", "update"]
    },
    Role.TECHNICIAN: {
        # Field technicians - limited to work orders and alerts
        "work_orders": ["read", "update"],
        "alerts": ["read", "acknowledge"],
        "hubs": ["read"],
        "buildings": ["read"],
        "units": ["read"],
        "contractors": ["read"],
        "documents": ["create", "read"]
    },
    Role.READ_ONLY: {
        # Read-only access for auditors, accountants, etc.
        "deployments": ["read"],
        "hubs": ["read"],
        "work_orders": ["read"],
        "alerts": ["read"],
        "tenants": ["read"],
        "leases": ["read"],
        "payments": ["read"],
        "clients": ["read"],
        "buildings": ["read"],
        "units": ["read"],
        "properties": ["read"],
        "service_packages": ["read"],
        "service_contracts": ["read"],
        "documents": ["read"],
        "contractors": ["read"],
        "audit_logs": ["read"]
    }
}


def has_permission(role: Role, resource: str, action: str) -> bool:
    """
    Check if role has permission for action on resource

    Args:
        role: User's role
        resource: Resource name (e.g., "deployments", "hubs")
        action: Action to perform (e.g., "create", "read", "update", "delete")

    Returns:
        True if role has permission, False otherwise
    """
    permissions = ROLE_PERMISSIONS.get(role, {}).get(resource, [])
    return action in permissions


def get_all_permissions(role: Role) -> dict:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role, {})


def get_current_user_role(request: Request) -> Role:
    """
    Extract current user's role from request

    This is a placeholder implementation that reads from Authelia headers.
    In production, you would:
    1. Extract user ID from auth headers (X-Forwarded-User)
    2. Look up user in database
    3. Return their assigned role

    For now, we'll use a header-based approach:
    - X-User-Role header (set by Authelia or custom middleware)
    - Defaults to READ_ONLY for safety
    """
    # Try to get role from header (set by Authelia or auth middleware)
    role_str = request.headers.get("X-User-Role", "read_only").lower()

    # Try to get from request state (set by auth dependency)
    if hasattr(request.state, "user_role"):
        role_str = request.state.user_role

    # Validate and convert to Role enum
    try:
        return Role(role_str)
    except ValueError:
        logger.warning(f"Invalid role '{role_str}', defaulting to READ_ONLY")
        return Role.READ_ONLY


def get_current_user_info(request: Request) -> dict:
    """
    Extract current user information from request

    Returns dict with:
    - user_id: Username or ID
    - role: User's role
    - email: User's email (if available)
    """
    user_id = request.headers.get("X-Forwarded-User", "anonymous")
    email = request.headers.get("X-Forwarded-Email", "")
    role = get_current_user_role(request)

    return {
        "user_id": user_id,
        "role": role,
        "email": email
    }


# FastAPI dependency for getting current role
async def get_current_role(request: Request) -> Role:
    """FastAPI dependency to inject current user's role"""
    return get_current_user_role(request)


def require_role(*allowed_roles: Role):
    """
    Decorator to require specific roles for endpoint access

    Usage:
        @router.post("/deployments")
        @require_role(Role.ADMIN, Role.OPERATOR)
        async def create_deployment(...):
            pass

    Args:
        *allowed_roles: Roles that are allowed to access this endpoint

    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            current_role = get_current_user_role(request)

            if current_role not in allowed_roles:
                logger.warning(
                    f"Access denied: User with role '{current_role}' attempted to access "
                    f"endpoint requiring roles: {[r.value for r in allowed_roles]}"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Insufficient permissions",
                        "required_roles": [r.value for r in allowed_roles],
                        "your_role": current_role.value
                    }
                )

            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator


def require_permission(resource: str, action: str):
    """
    Decorator to require specific permission for endpoint access

    This is more granular than role-based access.
    It checks the ROLE_PERMISSIONS matrix to see if the user's role
    has permission to perform the action on the resource.

    Usage:
        @router.post("/deployments")
        @require_permission("deployments", "create")
        async def create_deployment(...):
            pass

    Args:
        resource: Resource name (e.g., "deployments", "hubs")
        action: Action to perform (e.g., "create", "read", "update", "delete")

    Raises:
        HTTPException: 403 if user doesn't have required permission
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            current_role = get_current_user_role(request)
            user_info = get_current_user_info(request)

            if not has_permission(current_role, resource, action):
                logger.warning(
                    f"Access denied: User '{user_info['user_id']}' with role '{current_role}' "
                    f"attempted to perform '{action}' on '{resource}'"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Insufficient permissions",
                        "required_permission": f"{action} on {resource}",
                        "your_role": current_role.value
                    }
                )

            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator


# Convenience decorators for common permission patterns
def require_create(resource: str):
    """Shorthand for require_permission(resource, "create")"""
    return require_permission(resource, "create")


def require_read(resource: str):
    """Shorthand for require_permission(resource, "read")"""
    return require_permission(resource, "read")


def require_update(resource: str):
    """Shorthand for require_permission(resource, "update")"""
    return require_permission(resource, "update")


def require_delete(resource: str):
    """Shorthand for require_permission(resource, "delete")"""
    return require_permission(resource, "delete")


# Admin-only decorator
def admin_only():
    """Decorator to restrict endpoint to admins only"""
    return require_role(Role.ADMIN)
