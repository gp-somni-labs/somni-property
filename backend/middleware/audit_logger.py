"""
Audit Logging Middleware
Logs all API requests with user, timestamp, and action details

EPIC K: Enhanced with database logging to audit_logs table
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import time
import json
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log all API requests for audit trail

    Logs:
    - User (from Authelia headers)
    - Timestamp
    - HTTP method and path
    - Status code
    - Response time
    - Request body (for mutations)

    EPIC K: Critical actions are also logged to database audit_logs table
    """

    def __init__(self, app, db_session_factory: Optional[sessionmaker] = None):
        """
        Initialize audit logger middleware

        Args:
            app: FastAPI app
            db_session_factory: Optional SQLAlchemy session factory for DB logging
        """
        super().__init__(app)
        self.db_session_factory = db_session_factory

    async def dispatch(self, request: Request, call_next):
        # Get request details
        start_time = time.time()
        user = request.headers.get("X-Forwarded-User", "anonymous")
        user_email = request.headers.get("X-Forwarded-Email", "")
        method = request.method
        path = request.url.path

        # Get request body for mutations (POST, PUT, PATCH, DELETE)
        request_body = None
        content_type = request.headers.get("content-type", "")

        # Skip body reading for file uploads (multipart/form-data)
        # to avoid decoding binary data as UTF-8
        is_file_upload = "multipart/form-data" in content_type.lower()

        if method in ["POST", "PUT", "PATCH", "DELETE"] and not is_file_upload:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    request_body = body_bytes.decode()
                # Important: Need to recreate request with body for downstream
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception as e:
                logger.error(f"Error reading request body: {e}")

        # Process request
        response = await call_next(request)

        # Calculate response time
        duration = time.time() - start_time

        # Log audit entry
        audit_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "user_email": user_email,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }

        # Add request body for mutations
        if request_body and len(request_body) < 1000:  # Don't log huge bodies
            try:
                audit_entry["request_data"] = json.loads(request_body)
            except:
                pass

        # Log based on status code
        if response.status_code >= 500:
            logger.error(f"AUDIT: {json.dumps(audit_entry)}")
        elif response.status_code >= 400:
            logger.warning(f"AUDIT: {json.dumps(audit_entry)}")
        elif method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Log all mutations at INFO level
            logger.info(f"AUDIT: {json.dumps(audit_entry)}")
        else:
            # Log reads at DEBUG level
            logger.debug(f"AUDIT: {json.dumps(audit_entry)}")

        # Add response time header
        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

        # Log to database for critical actions (if DB session factory is available)
        if self.db_session_factory and self._should_log_to_db(method, path, response.status_code):
            try:
                self._log_to_database(
                    user=user,
                    user_email=user_email,
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                    request_body=request_body,
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to write audit log to database: {e}")

        return response

    def _should_log_to_db(self, method: str, path: str, status_code: int) -> bool:
        """
        Determine if this request should be logged to database

        We log to database for:
        - All mutations (POST, PUT, PATCH, DELETE)
        - Critical endpoints (deployments, leases, payments, etc.)
        - Failed requests (4xx, 5xx)
        """
        # Skip health check and metrics endpoints
        if path in ["/health", "/metrics", "/api/health"]:
            return False

        # Log all mutations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return True

        # Log failed requests
        if status_code >= 400:
            return True

        return False

    def _log_to_database(
        self,
        user: str,
        user_email: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_body: Optional[str],
        request: Request
    ):
        """Log audit entry to database"""
        from db.models import AuditLog

        # Extract resource type and ID from path
        resource_type, resource_id = self._extract_resource_from_path(path)

        # Determine action from method and path
        action = self._determine_action(method, path, resource_type)

        # Get user role from headers
        user_role = request.headers.get("X-User-Role", "unknown")

        # Get client IP
        ip_address = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)

        # Parse request body for changes
        changes = None
        if request_body and method in ["PUT", "PATCH"]:
            try:
                changes = {"new": json.loads(request_body)}
            except:
                pass

        # Create audit log entry
        db_session = self.db_session_factory()
        try:
            audit_log = AuditLog(
                user_id=user,
                user_email=user_email,
                user_role=user_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes,
                http_method=method,
                endpoint=path,
                ip_address=ip_address,
                user_agent=request.headers.get("User-Agent", ""),
                status_code=status_code,
                success=(status_code < 400),
                duration_ms=int(duration_ms)
            )
            db_session.add(audit_log)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to insert audit log: {e}")
        finally:
            db_session.close()

    def _extract_resource_from_path(self, path: str) -> tuple[str, Optional[uuid.UUID]]:
        """
        Extract resource type and ID from API path

        Examples:
            /api/v1/deployments -> ("deployments", None)
            /api/v1/deployments/123 -> ("deployments", "123")
            /api/v1/hubs/456/restart -> ("hubs", "456")
        """
        parts = path.split("/")

        # Find resource name (usually after /api/v1/)
        resource_type = "unknown"
        resource_id = None

        try:
            if "api" in parts and "v1" in parts:
                api_idx = parts.index("api")
                v1_idx = parts.index("v1")
                if v1_idx + 1 < len(parts):
                    resource_type = parts[v1_idx + 1]

                    # Try to find UUID in next part
                    if v1_idx + 2 < len(parts):
                        potential_id = parts[v1_idx + 2]
                        # Check if it looks like a UUID
                        try:
                            resource_id = uuid.UUID(potential_id)
                        except ValueError:
                            pass
        except ValueError:
            pass

        return resource_type, resource_id

    def _determine_action(self, method: str, path: str, resource_type: str) -> str:
        """
        Determine action name from HTTP method and path

        Examples:
            POST /api/v1/deployments -> "created_deployment"
            PUT /api/v1/hubs/123 -> "updated_hub"
            DELETE /api/v1/leases/456 -> "deleted_lease"
            POST /api/v1/hubs/123/restart -> "restarted_hub"
        """
        # Check for special actions (like restart, sync, etc.)
        path_lower = path.lower()
        if "restart" in path_lower:
            return f"restarted_{resource_type.rstrip('s')}"
        if "sync" in path_lower:
            return f"synced_{resource_type.rstrip('s')}"
        if "deploy" in path_lower:
            return f"deployed_{resource_type.rstrip('s')}"

        # Standard CRUD actions
        action_map = {
            "POST": "created",
            "PUT": "updated",
            "PATCH": "updated",
            "DELETE": "deleted",
            "GET": "read"
        }

        action = action_map.get(method, "accessed")
        # Convert plural to singular (deployments -> deployment)
        singular_resource = resource_type.rstrip('s')

        return f"{action}_{singular_resource}"
