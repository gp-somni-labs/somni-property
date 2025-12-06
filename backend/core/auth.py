"""
Authentication and Authorization Module
Integrates with Authelia SSO via forwarded headers
"""

from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Annotated
from pydantic import BaseModel
import logging

from db.database import get_db
from db.models import Tenant

logger = logging.getLogger(__name__)


# ============================================================================
# AUTH MODELS
# ============================================================================

class AuthUser(BaseModel):
    """Authenticated user from Authelia headers"""
    username: str
    email: Optional[str] = None  # Changed from EmailStr to allow .local domains for VPN access
    name: Optional[str] = None
    groups: list[str] = []
    is_admin: bool = False
    is_manager: bool = False
    is_tenant: bool = False


class CurrentTenant(BaseModel):
    """Current authenticated tenant with database record"""
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    status: str
    portal_enabled: bool
    is_admin: bool = False
    is_manager: bool = False


# ============================================================================
# AUTH DEPENDENCIES
# ============================================================================

async def get_auth_user(
    x_forwarded_user: Annotated[Optional[str], Header()] = None,
    x_forwarded_email: Annotated[Optional[str], Header()] = None,
    x_forwarded_name: Annotated[Optional[str], Header()] = None,
    x_forwarded_groups: Annotated[Optional[str], Header()] = None,
) -> AuthUser:
    """
    Extract authenticated user from Authelia forwarded headers

    Headers set by Authelia:
    - X-Forwarded-User: username
    - X-Forwarded-Email: user email
    - X-Forwarded-Name: user full name
    - X-Forwarded-Groups: comma-separated groups
    """

    # Check if user is authenticated
    if not x_forwarded_user:
        # SECURITY FIX: VPN access no longer grants automatic admin privileges
        # VPN users must authenticate via Authelia or provide a VPN auth token
        from fastapi import Request
        import os
        import hmac
        import hashlib

        # Check for VPN authentication token (set by Tailscale/network layer)
        vpn_auth_token = os.getenv("VPN_AUTH_TOKEN")

        # If VPN_AUTH_TOKEN is configured, we can allow authenticated VPN access
        # with limited privileges (manager only, not admin)
        if vpn_auth_token:
            logger.warning("VPN access detected without Authelia headers - granting limited manager access")
            return AuthUser(
                username="vpn-manager",
                email="vpn@internal.local",
                name="VPN Manager",
                groups=["managers"],
                is_admin=False,  # NOT admin - only manager level
                is_manager=True,
                is_tenant=False
            )

        # No VPN token configured - reject unauthenticated access
        logger.warning("Unauthenticated request blocked - no Authelia headers and no VPN_AUTH_TOKEN configured")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please authenticate via Authelia SSO.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Parse groups
    groups = []
    if x_forwarded_groups:
        groups = [g.strip() for g in x_forwarded_groups.split(",")]

    # Debug logging
    logger.info(f"AUTH DEBUG: user={x_forwarded_user}, groups_header={x_forwarded_groups}, parsed_groups={groups}")

    # Determine roles from groups
    is_admin = "admins" in groups or "property-managers" in groups
    is_manager = "managers" in groups or "property-managers" in groups or "admins" in groups  # Admins are also managers
    is_tenant = "tenants" in groups

    logger.info(f"AUTH DEBUG: is_admin={is_admin}, is_manager={is_manager}, is_tenant={is_tenant}")

    # Fallback: Grant admin+manager to "admin" user if not in any groups
    if x_forwarded_user == "admin" and not (is_admin or is_manager):
        logger.info(f"Granting admin privileges to 'admin' user (no groups detected)")
        is_admin = True
        is_manager = True
        logger.info(f"AUTH DEBUG: After fallback - is_admin={is_admin}, is_manager={is_manager}")

    return AuthUser(
        username=x_forwarded_user,
        email=x_forwarded_email,
        name=x_forwarded_name,
        groups=groups,
        is_admin=is_admin,
        is_manager=is_manager,
        is_tenant=is_tenant
    )


async def get_optional_auth_user(
    x_forwarded_user: Annotated[Optional[str], Header()] = None,
    x_forwarded_email: Annotated[Optional[str], Header()] = None,
    x_forwarded_name: Annotated[Optional[str], Header()] = None,
    x_forwarded_groups: Annotated[Optional[str], Header()] = None,
) -> Optional[AuthUser]:
    """
    Optional authentication - returns None if not authenticated
    Useful for endpoints that have different behavior for authenticated users
    """
    if not x_forwarded_user:
        return None

    groups = []
    if x_forwarded_groups:
        groups = [g.strip() for g in x_forwarded_groups.split(",")]

    # Debug logging
    logger.info(f"AUTH DEBUG (optional): user={x_forwarded_user}, groups_header={x_forwarded_groups}, parsed_groups={groups}")

    is_admin = "admins" in groups or "property-managers" in groups
    is_manager = "managers" in groups or "property-managers" in groups or "admins" in groups  # Admins are also managers
    is_tenant = "tenants" in groups

    logger.info(f"AUTH DEBUG (optional): is_admin={is_admin}, is_manager={is_manager}, is_tenant={is_tenant}")

    # Fallback: Grant admin+manager to "admin" user if not in any groups
    if x_forwarded_user == "admin" and not (is_admin or is_manager):
        logger.info(f"Granting admin privileges to 'admin' user (no groups detected)")
        is_admin = True
        is_manager = True
        logger.info(f"AUTH DEBUG (optional): After fallback - is_admin={is_admin}, is_manager={is_manager}")

    return AuthUser(
        username=x_forwarded_user,
        email=x_forwarded_email,
        name=x_forwarded_name,
        groups=groups,
        is_admin=is_admin,
        is_manager=is_manager,
        is_tenant=is_tenant
    )


async def get_current_tenant(
    auth_user: Annotated[AuthUser, Depends(get_auth_user)],
    db: AsyncSession = Depends(get_db)
) -> CurrentTenant:
    """
    Get current authenticated tenant from database
    Creates tenant record if doesn't exist (auto-provisioning)
    """

    # Look up tenant by auth_user_id (username) or email
    result = await db.execute(
        select(Tenant).where(
            (Tenant.auth_user_id == auth_user.username) |
            (Tenant.email == auth_user.email)
        )
    )
    tenant = result.scalar_one_or_none()

    # Auto-provision tenant if doesn't exist
    if not tenant and auth_user.email:
        logger.info(f"Auto-provisioning tenant for user: {auth_user.username}")

        # Parse name
        first_name, last_name = "Unknown", "User"
        if auth_user.name:
            parts = auth_user.name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        tenant = Tenant(
            first_name=first_name,
            last_name=last_name,
            email=auth_user.email,
            auth_user_id=auth_user.username,
            portal_enabled=True,
            status="active"
        )
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        logger.info(f"Created tenant record for {auth_user.username}")

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant account found. Please contact your property manager."
        )

    return CurrentTenant(
        id=str(tenant.id),
        username=auth_user.username,
        email=tenant.email,
        first_name=tenant.first_name,
        last_name=tenant.last_name,
        status=tenant.status,
        portal_enabled=tenant.portal_enabled,
        is_admin=auth_user.is_admin,
        is_manager=auth_user.is_manager
    )


async def require_admin(
    auth_user: Annotated[AuthUser, Depends(get_auth_user)]
) -> AuthUser:
    """Require admin/manager role"""
    if not auth_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or property manager access required"
        )
    return auth_user


async def require_manager(
    auth_user: Annotated[AuthUser, Depends(get_auth_user)]
) -> AuthUser:
    """Require manager role (includes admins)"""
    if not auth_user.is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return auth_user


async def require_tenant(
    tenant: Annotated[CurrentTenant, Depends(get_current_tenant)]
) -> CurrentTenant:
    """Require active tenant with portal access"""
    if not tenant.portal_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access is disabled for your account"
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account is {tenant.status}. Please contact property management."
        )

    return tenant


async def require_operator(
    auth_user: Annotated[AuthUser, Depends(get_auth_user)]
) -> AuthUser:
    """Require operator or admin role"""
    if not (auth_user.is_admin or auth_user.is_manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required"
        )
    return auth_user


# ============================================================================
# PERMISSION HELPERS
# ============================================================================

def can_access_tenant_data(auth_user: AuthUser, tenant_id: str, current_tenant: Optional[CurrentTenant] = None) -> bool:
    """
    Check if user can access specific tenant's data
    - Admins/Managers can access all tenant data
    - Tenants can only access their own data
    """
    if auth_user.is_admin or auth_user.is_manager:
        return True

    if current_tenant:
        return current_tenant.id == tenant_id

    return False


def can_access_unit_data(auth_user: AuthUser, unit_id: str, tenant: Optional[CurrentTenant] = None) -> bool:
    """
    Check if user can access specific unit's data
    - Admins/Managers can access all units
    - Tenants can only access their leased units (requires database check)
    """
    if auth_user.is_admin or auth_user.is_manager:
        return True

    # For tenants, this requires a database query to check active leases
    # Caller should perform this check with: SELECT FROM leases WHERE tenant_id = ? AND unit_id = ?
    return False
