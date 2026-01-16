"""License Enforcement Middleware for Alphha DMS"""
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.database import SessionLocal
from app.services.license_service import LicenseService


# Routes that don't require license check
EXEMPT_ROUTES = [
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/v1/license",  # License management endpoints
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
]


class LicenseMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce license validation.

    - Adds license warning headers when license is expiring soon
    - Blocks access when license is expired (past grace period)
    - Allows read-only access during grace period
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip exempt routes
        path = request.url.path
        if any(path.startswith(exempt) for exempt in EXEMPT_ROUTES):
            return await call_next(request)

        # Get tenant from auth or request
        tenant_id = self._get_tenant_id(request)
        if not tenant_id:
            # No tenant context - allow request (auth will handle it)
            return await call_next(request)

        # Check license status
        db = SessionLocal()
        try:
            license_status = LicenseService.check_platform_access(db, tenant_id)

            # If license is not allowed and past grace period
            if not license_status["allowed"]:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "License expired. Platform access is restricted.",
                        "reason": license_status["reason"],
                        "code": "LICENSE_EXPIRED"
                    }
                )

            # Process the request
            response = await call_next(request)

            # Add license warning headers
            if license_status.get("in_grace_period"):
                response.headers["X-License-Warning"] = "License expired - in grace period"
                response.headers["X-License-Status"] = "grace_period"

            if license_status.get("expires_at"):
                expires_at = license_status["expires_at"]
                if isinstance(expires_at, datetime):
                    days_remaining = (expires_at - datetime.utcnow()).days

                    # Add warning if expiring within 30 days
                    if days_remaining <= 30 and not license_status.get("in_grace_period"):
                        response.headers["X-License-Warning"] = f"License expires in {days_remaining} days"
                        response.headers["X-License-Days-Remaining"] = str(days_remaining)
                        response.headers["X-License-Status"] = "expiring_soon"
                    else:
                        response.headers["X-License-Status"] = "valid"

            return response

        finally:
            db.close()

    def _get_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from the request"""
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id

        # Try to get from header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            return tenant_header

        # Try to get from auth token (if present)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Would need to decode JWT here, but for simplicity we'll let auth handle it
            pass

        return None


def create_license_dependency():
    """Create a FastAPI dependency for license checking"""
    from fastapi import Depends, HTTPException, status
    from app.api.v1.dependencies import get_current_user, get_db

    async def check_license(
        db: SessionLocal = Depends(get_db),
        current_user = Depends(get_current_user)
    ):
        """Dependency to check license status"""
        if not current_user or not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        license_status = LicenseService.check_platform_access(db, current_user.tenant_id)

        if not license_status["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=license_status["reason"],
                headers={"X-License-Status": "expired"}
            )

        return {
            "valid": True,
            "in_grace_period": license_status.get("in_grace_period", False),
            "expires_at": license_status.get("expires_at"),
        }

    return check_license


# Dependency instance
check_license = create_license_dependency()
