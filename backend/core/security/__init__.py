"""
Security Module
Contains authentication, authorization, and RBAC functionality
"""

from .rbac import (
    Role,
    ROLE_PERMISSIONS,
    has_permission,
    get_all_permissions,
    get_current_user_role,
    get_current_user_info,
    get_current_role,
    require_role,
    require_permission,
    require_create,
    require_read,
    require_update,
    require_delete,
    admin_only
)

__all__ = [
    'Role',
    'ROLE_PERMISSIONS',
    'has_permission',
    'get_all_permissions',
    'get_current_user_role',
    'get_current_user_info',
    'get_current_role',
    'require_role',
    'require_permission',
    'require_create',
    'require_read',
    'require_update',
    'require_delete',
    'admin_only'
]
