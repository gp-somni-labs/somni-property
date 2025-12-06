"""
SomniProperty Custom Exception Hierarchy

Provides structured exception handling with:
- Consistent error codes for client/server error distinction
- Request ID correlation for debugging
- User-friendly messages separate from technical details
- Proper HTTP status code mapping
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class SomniPropertyException(Exception):
    """
    Base exception for all SomniProperty application errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.
    """
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize the exception.

        Args:
            message: User-friendly error message
            details: Additional context (not exposed to client in production)
            original_exception: The underlying exception that caused this error
        """
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(message)

    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "code": self.error_code,
            "message": self.message,
        }
        if include_details and self.details:
            result["details"] = self.details
        return result


# =============================================================================
# VALIDATION ERRORS (400)
# =============================================================================

class ValidationError(SomniPropertyException):
    """Invalid input data or request parameters."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"


class InvalidInputError(ValidationError):
    """Specific field validation failure."""
    error_code = "INVALID_INPUT"

    def __init__(self, field: str, message: str, value: Any = None):
        details = {"field": field}
        if value is not None:
            details["provided_value"] = str(value)[:100]  # Truncate for safety
        super().__init__(message=f"Invalid {field}: {message}", details=details)


class MissingRequiredFieldError(ValidationError):
    """Required field is missing."""
    error_code = "MISSING_FIELD"

    def __init__(self, field: str):
        super().__init__(
            message=f"Required field '{field}' is missing",
            details={"field": field}
        )


# =============================================================================
# AUTHENTICATION ERRORS (401)
# =============================================================================

class AuthenticationError(SomniPropertyException):
    """User is not authenticated."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTH_ERROR"

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message)


class TokenExpiredError(AuthenticationError):
    """Authentication token has expired."""
    error_code = "TOKEN_EXPIRED"

    def __init__(self):
        super().__init__(message="Your session has expired. Please log in again.")


class InvalidTokenError(AuthenticationError):
    """Authentication token is invalid."""
    error_code = "INVALID_TOKEN"

    def __init__(self):
        super().__init__(message="Invalid authentication token.")


# =============================================================================
# AUTHORIZATION ERRORS (403)
# =============================================================================

class AuthorizationError(SomniPropertyException):
    """User does not have permission for this action."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        resource: Optional[str] = None,
        action: Optional[str] = None
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action
        super().__init__(message=message, details=details)


class UnauthorizedAccessError(AuthorizationError):
    """User doesn't have permission to access resource (backwards compatibility)."""
    error_code = "UNAUTHORIZED_ACCESS"

    def __init__(self, message: str = "You don't have permission to access this resource"):
        super().__init__(message=message)


class InsufficientPermissionsError(AuthorizationError):
    """User lacks specific permissions."""
    error_code = "INSUFFICIENT_PERMISSIONS"

    def __init__(self, required_role: str):
        super().__init__(
            message=f"This action requires {required_role} privileges",
            details={"required_role": required_role}
        )


class TenantIsolationError(AuthorizationError):
    """Attempted access to another tenant's data."""
    error_code = "TENANT_ISOLATION_VIOLATION"

    def __init__(self):
        super().__init__(
            message="You can only access your own data"
        )


# =============================================================================
# NOT FOUND ERRORS (404)
# =============================================================================

class ResourceNotFoundError(SomniPropertyException):
    """Requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"

    def __init__(self, resource_type: str, resource_id: Optional[str] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            message=message,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class PropertyNotFoundError(ResourceNotFoundError):
    """Property does not exist."""
    error_code = "PROPERTY_NOT_FOUND"

    def __init__(self, property_id: str):
        super().__init__("Property", property_id)


class TenantNotFoundError(ResourceNotFoundError):
    """Tenant does not exist."""
    error_code = "TENANT_NOT_FOUND"

    def __init__(self, tenant_id: str):
        super().__init__("Tenant", tenant_id)


class ClientNotFoundError(ResourceNotFoundError):
    """Client does not exist."""
    error_code = "CLIENT_NOT_FOUND"

    def __init__(self, client_id: str):
        super().__init__("Client", client_id)


class QuoteNotFoundError(ResourceNotFoundError):
    """Quote does not exist."""
    error_code = "QUOTE_NOT_FOUND"

    def __init__(self, quote_id: str):
        super().__init__("Quote", quote_id)


class InvoiceNotFoundError(ResourceNotFoundError):
    """Invoice does not exist."""
    error_code = "INVOICE_NOT_FOUND"

    def __init__(self, invoice_id: str):
        super().__init__("Invoice", invoice_id)


# =============================================================================
# CONFLICT ERRORS (409)
# =============================================================================

class ConflictError(SomniPropertyException):
    """Resource state conflict."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class DuplicateResourceError(ConflictError):
    """Resource already exists."""
    error_code = "DUPLICATE_RESOURCE"

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"A {resource_type} with identifier '{identifier}' already exists",
            details={"resource_type": resource_type, "identifier": identifier}
        )


class InvalidStateTransitionError(ConflictError):
    """Invalid state change attempted."""
    error_code = "INVALID_STATE_TRANSITION"

    def __init__(self, current_state: str, attempted_state: str, resource_type: str = "Resource"):
        super().__init__(
            message=f"Cannot change {resource_type} from '{current_state}' to '{attempted_state}'",
            details={
                "current_state": current_state,
                "attempted_state": attempted_state
            }
        )


# =============================================================================
# UNPROCESSABLE ENTITY ERRORS (422)
# =============================================================================

class BusinessLogicError(SomniPropertyException):
    """Business rule violation."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "BUSINESS_LOGIC_ERROR"


class QuoteCalculationError(BusinessLogicError):
    """Error calculating quote pricing."""
    error_code = "QUOTE_CALC_ERROR"

    def __init__(self, message: str, calculation_details: Optional[Dict] = None):
        super().__init__(
            message=f"Quote calculation failed: {message}",
            details=calculation_details
        )


class PaymentProcessingError(BusinessLogicError):
    """Payment could not be processed."""
    error_code = "PAYMENT_ERROR"

    def __init__(self, message: str, transaction_id: Optional[str] = None):
        details = {}
        if transaction_id:
            details["transaction_id"] = transaction_id
        super().__init__(message=message, details=details)


class SchedulingConflictError(BusinessLogicError):
    """Scheduling conflict detected."""
    error_code = "SCHEDULING_CONFLICT"

    def __init__(self, message: str, conflicting_booking: Optional[str] = None):
        details = {}
        if conflicting_booking:
            details["conflicting_booking"] = conflicting_booking
        super().__init__(message=message, details=details)


# =============================================================================
# DATABASE ERRORS (500)
# =============================================================================

class DatabaseError(SomniPropertyException):
    """Database operation failed."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DATABASE_ERROR"

    def __init__(self, message: str):
        super().__init__(message=f"Database error: {message}")


# =============================================================================
# EXTERNAL SERVICE ERRORS (502)
# =============================================================================

class ExternalServiceError(SomniPropertyException):
    """External service failure."""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service_name: str, message: str, original_error: Optional[str] = None):
        details = {"service": service_name}
        if original_error:
            details["original_error"] = original_error
        super().__init__(
            message=f"{service_name} service error: {message}",
            details=details
        )
        self.service_name = service_name


class InvoiceNinjaError(ExternalServiceError):
    """Invoice Ninja API error."""
    error_code = "INVOICENINJA_ERROR"

    def __init__(self, message: str, details: Optional[Dict] = None, original_error: Optional[str] = None):
        super().__init__("InvoiceNinja", message, original_error)
        if details:
            self.details.update(details)


class HomeAssistantError(ExternalServiceError):
    """Home Assistant API error."""
    error_code = "HOMEASSISTANT_ERROR"

    def __init__(self, message: str, original_error: Optional[str] = None):
        super().__init__("HomeAssistant", message, original_error)


class StripeError(ExternalServiceError):
    """Stripe API error."""
    error_code = "STRIPE_ERROR"

    def __init__(self, message: str, details: Optional[Dict] = None, original_error: Optional[str] = None):
        super().__init__("Stripe", message, original_error)
        if details:
            self.details.update(details)


class CalComError(ExternalServiceError):
    """Cal.com API error."""
    error_code = "CALCOM_ERROR"

    def __init__(self, message: str, details: Optional[Dict] = None, original_error: Optional[str] = None):
        super().__init__("Cal.com", message, original_error)
        if details:
            self.details.update(details)


class KubernetesError(ExternalServiceError):
    """Kubernetes API error."""
    error_code = "KUBERNETES_ERROR"

    def __init__(self, message: str, details: Optional[Dict] = None, original_error: Optional[str] = None):
        super().__init__("Kubernetes", message, original_error)
        if details:
            self.details.update(details)


# =============================================================================
# SERVICE UNAVAILABLE ERRORS (503)
# =============================================================================

class ServiceUnavailableError(SomniPropertyException):
    """Service temporarily unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(self, service_name: str, retry_after: Optional[int] = None):
        details = {"service": service_name}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=f"{service_name} is temporarily unavailable. Please try again later.",
            details=details
        )


class DatabaseUnavailableError(ServiceUnavailableError):
    """Database connection unavailable."""
    error_code = "DATABASE_UNAVAILABLE"

    def __init__(self):
        super().__init__("Database", retry_after=30)


class MQTTUnavailableError(ServiceUnavailableError):
    """MQTT broker unavailable."""
    error_code = "MQTT_UNAVAILABLE"

    def __init__(self):
        super().__init__("MQTT", retry_after=60)


# =============================================================================
# RATE LIMIT ERRORS (429)
# =============================================================================

class RateLimitExceededError(SomniPropertyException):
    """Rate limit exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Too many requests. Please slow down.",
            details={"retry_after_seconds": retry_after}
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def to_http_exception(exc: SomniPropertyException, request_id: Optional[str] = None) -> HTTPException:
    """
    Convert a SomniPropertyException to a FastAPI HTTPException.

    Args:
        exc: The custom exception
        request_id: Optional request ID for correlation

    Returns:
        HTTPException with standardized error response
    """
    content = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
        }
    }
    if request_id:
        content["error"]["request_id"] = request_id

    return HTTPException(
        status_code=exc.status_code,
        detail=content["error"]
    )


# Convenience functions to raise HTTP exceptions (backwards compatibility)
def raise_not_found(resource_type: str, resource_id: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource_type} with ID {resource_id} not found"
    )


def raise_unauthorized(message: str = "Unauthorized"):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def raise_bad_request(message: str):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Base exception
    "SomniPropertyException",

    # Validation errors (400)
    "ValidationError",
    "InvalidInputError",
    "MissingRequiredFieldError",

    # Authentication errors (401)
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",

    # Authorization errors (403)
    "AuthorizationError",
    "UnauthorizedAccessError",
    "InsufficientPermissionsError",
    "TenantIsolationError",

    # Not found errors (404)
    "ResourceNotFoundError",
    "PropertyNotFoundError",
    "TenantNotFoundError",
    "ClientNotFoundError",
    "QuoteNotFoundError",
    "InvoiceNotFoundError",

    # Conflict errors (409)
    "ConflictError",
    "DuplicateResourceError",
    "InvalidStateTransitionError",

    # Business logic errors (422)
    "BusinessLogicError",
    "QuoteCalculationError",
    "PaymentProcessingError",
    "SchedulingConflictError",

    # Database errors (500)
    "DatabaseError",

    # External service errors (502)
    "ExternalServiceError",
    "InvoiceNinjaError",
    "HomeAssistantError",
    "StripeError",
    "CalComError",
    "KubernetesError",

    # Service unavailable errors (503)
    "ServiceUnavailableError",
    "DatabaseUnavailableError",
    "MQTTUnavailableError",

    # Rate limit errors (429)
    "RateLimitExceededError",

    # Helper functions
    "to_http_exception",
    "raise_not_found",
    "raise_unauthorized",
    "raise_bad_request",
]
