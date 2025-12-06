"""
Rate Limiting Middleware
Prevents API abuse by limiting requests per user/IP
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit requests per user or IP address

    Default: 100 requests per minute per user
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = defaultdict(list)
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.now()

    def _cleanup_old_requests(self):
        """Remove requests older than 1 minute"""
        if datetime.now() - self.last_cleanup > self.cleanup_interval:
            cutoff = datetime.now() - timedelta(minutes=1)
            for key in list(self.request_counts.keys()):
                self.request_counts[key] = [
                    req_time for req_time in self.request_counts[key]
                    if req_time > cutoff
                ]
                if not self.request_counts[key]:
                    del self.request_counts[key]
            self.last_cleanup = datetime.now()

    async def dispatch(self, request: Request, call_next):
        # Get user identifier (prefer authenticated user, fallback to IP)
        user = request.headers.get("X-Forwarded-User") or request.client.host

        # Clean up old requests periodically
        self._cleanup_old_requests()

        # Check rate limit
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        # Get requests in last minute
        recent_requests = [
            req_time for req_time in self.request_counts[user]
            if req_time > cutoff
        ]

        if len(recent_requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {user}: {len(recent_requests)} requests/min")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."
            )

        # Record this request
        self.request_counts[user].append(now)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(recent_requests) - 1
        )

        return response
