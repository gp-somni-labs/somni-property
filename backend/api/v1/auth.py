"""
Authentication API - Employee/Staff Authentication via Infisical
Validates credentials stored in Infisical, issues JWT tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import jwt
import bcrypt
import logging
import os

from db.database import get_db

router = APIRouter(tags=["auth"])
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("CUSTOMER_PORTAL_SECRET_KEY", "change-me-in-production"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    first_name: str
    last_name: str
    role: str
    permissions: List[str] = []
    department: Optional[str] = None
    position: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# =============================================================================
# INFISICAL EMPLOYEE SERVICE
# =============================================================================

class InfisicalEmployeeService:
    """Service to fetch and validate employee credentials from Infisical"""

    def __init__(self):
        from services.infisical_api_client import InfisicalAPIClient
        self.client = InfisicalAPIClient()

    async def get_employee_credentials(self, username: str) -> Optional[dict]:
        """
        Fetch employee credentials from Infisical

        Looks for secrets at path: /employees/{username}/
        Expected secrets:
        - password_hash: bcrypt hashed password
        - email: employee email
        - first_name: first name
        - last_name: last name
        - role: employee role (admin, manager, technician, etc.)
        - department: department (optional)
        - position: job title (optional)
        """
        try:
            await self.client._ensure_authenticated()

            # Get secrets from employee path
            response = await self.client.http_client.get(
                f"/v3/secrets/raw",
                params={
                    "workspaceId": self.client.project_id,
                    "environment": self.client.env_slug,
                    "secretPath": f"/employees/{username}"
                },
                headers=self.client._get_headers()
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            secrets = {}
            for secret in data.get("secrets", []):
                key = secret.get("secretKey", "").lower()
                value = secret.get("secretValue", "")
                secrets[key] = value

            if not secrets.get("password_hash"):
                logger.warning(f"No password_hash found for employee: {username}")
                return None

            return {
                "username": username,
                "password_hash": secrets.get("password_hash"),
                "email": secrets.get("email"),
                "first_name": secrets.get("first_name", username),
                "last_name": secrets.get("last_name", ""),
                "role": secrets.get("role", "employee"),
                "department": secrets.get("department"),
                "position": secrets.get("position"),
                "permissions": secrets.get("permissions", "").split(",") if secrets.get("permissions") else []
            }

        except Exception as e:
            logger.error(f"Failed to fetch employee credentials from Infisical: {e}")
            return None

    async def validate_password(self, password: str, password_hash: str) -> bool:
        """Validate password against bcrypt hash"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password validation error: {e}")
            return False

    async def close(self):
        await self.client.close()


# Global instance
_employee_service: Optional[InfisicalEmployeeService] = None


async def get_employee_service() -> InfisicalEmployeeService:
    global _employee_service
    if _employee_service is None:
        _employee_service = InfisicalEmployeeService()
    return _employee_service


# =============================================================================
# JWT TOKEN FUNCTIONS
# =============================================================================

def create_access_token(user_data: dict) -> str:
    """Create JWT access token"""
    expires = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_data["username"],
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "access",
        "user": {
            "username": user_data["username"],
            "email": user_data.get("email"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "role": user_data.get("role"),
            "permissions": user_data.get("permissions", [])
        }
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(username: str) -> str:
    """Create JWT refresh token"""
    expires = datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)
    payload = {
        "sub": username,
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user from JWT"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload.get("user", {})


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate employee with username/password from Infisical

    Returns JWT access and refresh tokens on success.
    """
    employee_service = await get_employee_service()

    # Get employee credentials from Infisical
    employee = await employee_service.get_employee_credentials(request.username)

    if not employee:
        logger.warning(f"Login attempt for unknown user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Validate password
    if not await employee_service.validate_password(request.password, employee["password_hash"]):
        logger.warning(f"Invalid password for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Generate tokens
    access_token = create_access_token(employee)
    refresh_token = create_refresh_token(request.username)

    logger.info(f"Successful login for user: {request.username}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user={
            "id": request.username,
            "username": request.username,
            "email": employee.get("email"),
            "first_name": employee.get("first_name"),
            "last_name": employee.get("last_name"),
            "role": employee.get("role"),
            "department": employee.get("department"),
            "position": employee.get("position"),
            "permissions": employee.get("permissions", [])
        }
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint - invalidates current session

    Note: For stateless JWT, this is a no-op on the server.
    Client should discard the tokens.
    """
    logger.info(f"User logged out: {current_user.get('username')}")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user's information
    """
    return UserResponse(
        id=current_user.get("username", ""),
        username=current_user.get("username", ""),
        email=current_user.get("email"),
        first_name=current_user.get("first_name", ""),
        last_name=current_user.get("last_name", ""),
        role=current_user.get("role", "employee"),
        permissions=current_user.get("permissions", []),
        department=current_user.get("department"),
        position=current_user.get("position")
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token
    """
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    username = payload.get("sub")

    # Get fresh employee data from Infisical
    employee_service = await get_employee_service()
    employee = await employee_service.get_employee_credentials(username)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists"
        )

    # Generate new tokens
    access_token = create_access_token(employee)
    new_refresh_token = create_refresh_token(username)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600
    }


@router.post("/2fa/verify")
async def verify_2fa(
    code: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify two-factor authentication code

    Note: TOTP verification not yet implemented.
    This is a placeholder for future 2FA support.
    """
    # TODO: Implement TOTP verification
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Two-factor authentication not yet implemented"
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password

    Note: This updates the password hash in Infisical.
    """
    employee_service = await get_employee_service()
    username = current_user.get("username")

    # Verify current password
    employee = await employee_service.get_employee_credentials(username)
    if not employee:
        raise HTTPException(status_code=404, detail="User not found")

    if not await employee_service.validate_password(request.current_password, employee["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Generate new password hash
    new_hash = bcrypt.hashpw(
        request.new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Update in Infisical
    try:
        await employee_service.client._ensure_authenticated()
        response = await employee_service.client.http_client.patch(
            f"/v3/secrets/raw/password_hash",
            params={
                "workspaceId": employee_service.client.project_id,
                "environment": employee_service.client.env_slug,
                "secretPath": f"/employees/{username}"
            },
            json={"secretValue": new_hash},
            headers=employee_service.client._get_headers()
        )
        response.raise_for_status()

        logger.info(f"Password changed for user: {username}")
        return {"success": True, "message": "Password changed successfully"}

    except Exception as e:
        logger.error(f"Failed to update password in Infisical: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
