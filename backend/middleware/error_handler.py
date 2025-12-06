"""
Error Handler Middleware
Catches all exceptions and returns proper structured error responses
with request ID correlation for debugging.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback

from core.exceptions import SomniPropertyException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler middleware.

    Catches all unhandled exceptions and returns structured error responses
    with proper HTTP status codes and request ID correlation.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except SomniPropertyException as exc:
            # Handle our custom exceptions with proper status codes
            request_id = getattr(request.state, "request_id", "unknown")
            user = request.headers.get("X-Forwarded-User", "anonymous")

            # Log with appropriate level based on status code
            if exc.status_code >= 500:
                logger.error(
                    f"[{request_id}] {exc.error_code}: {exc.message} "
                    f"(user={user}, path={request.url.path})",
                    extra={
                        "request_id": request_id,
                        "error_code": exc.error_code,
                        "user": user,
                        "path": request.url.path,
                        "details": exc.details
                    }
                )
            else:
                logger.warning(
                    f"[{request_id}] {exc.error_code}: {exc.message} "
                    f"(user={user}, path={request.url.path})"
                )

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.error_code,
                        "message": exc.message,
                        "request_id": request_id
                    }
                }
            )

        except Exception as exc:
            # Handle unexpected exceptions
            request_id = getattr(request.state, "request_id", "unknown")
            user = request.headers.get("X-Forwarded-User", "anonymous")

            # Log full traceback for unexpected errors (server-side only)
            logger.error(
                f"[{request_id}] UNHANDLED_EXCEPTION: {type(exc).__name__}: {str(exc)} "
                f"(user={user}, method={request.method}, path={request.url.path})\n"
                f"{traceback.format_exc()}",
                extra={
                    "request_id": request_id,
                    "exception_type": type(exc).__name__,
                    "user": user,
                    "method": request.method,
                    "path": request.url.path
                }
            )

            # Return generic error to client (don't expose internal details)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred. Please try again or contact support.",
                        "request_id": request_id
                    }
                }
            )
