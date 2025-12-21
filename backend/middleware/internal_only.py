"""Internal-only API middleware.

Restricts access to internal endpoints based on environment and client IP.
"""

from __future__ import annotations

import os
from typing import List

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class InternalOnlyMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access to internal endpoints.

    In production, only allows requests from localhost (127.0.0.1).
    In development, allows all requests for testing.
    """

    def __init__(self, app, allowed_hosts: List[str] | None = None):
        """
        Initialize the internal-only middleware.

        Args:
            app: The FastAPI application instance
            allowed_hosts: Optional list of allowed host addresses.
                          If None, defaults to localhost addresses.
        """
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["127.0.0.1", "localhost", "::1"]

    async def dispatch(self, request: Request, call_next):
        """Check if request is from allowed origin.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Raises:
            HTTPException: 403 if access denied in production

        Returns:
            Response from next handler if allowed
        """
        # Check ENVIRONMENT first, fallback to ENV for backward compatibility
        env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))

        # In production, restrict to allowed hosts only
        if env == "production":
            client_host = request.client.host if request.client else None

            if client_host not in self.allowed_hosts:
                # Log the unauthorized access attempt for security monitoring
                from backend.src.fi_common.logging.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "SECURITY_INTERNAL_API_ACCESS_ATTEMPT",
                    client_host=client_host,
                    path=request.url.path,
                    method=request.method,
                    user_agent=request.headers.get("user-agent"),
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Internal API endpoints are only accessible from allowed hosts",
                )

        # In development, allow all (for testing)
        return await call_next(request)
