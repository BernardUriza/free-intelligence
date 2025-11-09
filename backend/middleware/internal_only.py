"""Internal-only API middleware.

Restricts access to internal endpoints based on environment and client IP.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

import os


class InternalOnlyMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access to internal endpoints.

    In production, only allows requests from localhost (127.0.0.1).
    In development, allows all requests for testing.
    """

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
        env = os.getenv("ENV", "development")

        # In production, restrict to localhost only
        if env == "production":
            client_host = request.client.host if request.client else None

            # Allow localhost and 127.0.0.1
            if client_host not in ("127.0.0.1", "localhost", "::1"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Internal API endpoints are only accessible from localhost",
                )

        # In development, allow all (for testing)
        return await call_next(request)
