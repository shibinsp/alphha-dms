from typing import Optional
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user)
) -> str:
    """Get the current tenant ID from user context."""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a tenant"
        )
    return current_user.tenant_id


async def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Tenant:
    """Get the current tenant from user context or header."""
    # First try to get tenant from user
    if current_user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if tenant and tenant.is_active:
            # Check license
            if tenant.license_expires and tenant.license_expires < datetime.utcnow().date():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant license has expired"
                )
            return tenant

    # Try X-Tenant-ID header (for super admin)
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.is_active:
            return tenant

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tenant not found or inactive"
    )


def require_permissions(*permissions):
    """Dependency to check if user has required permissions."""
    # Flatten if a list was passed
    flat_permissions = []
    for p in permissions:
        if isinstance(p, list):
            flat_permissions.extend(p)
        else:
            flat_permissions.append(p)
    
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = set()

        # Gather permissions from all user roles
        for role in current_user.roles:
            if role.permissions:
                for perm in role.permissions:
                    if isinstance(perm, str):
                        user_permissions.add(perm)

        # Wildcard permission grants all access
        if "*" in user_permissions:
            return current_user

        # Check if user has all required permissions
        for permission in flat_permissions:
            # Check exact match or category wildcard (e.g., "documents:*")
            has_permission = (
                permission in user_permissions or
                f"{permission.split(':')[0]}:*" in user_permissions
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}"
                )

        return current_user

    return permission_checker


def require_any_permission(*permissions):
    """Dependency to check if user has at least one of the required permissions."""
    # Flatten if a list was passed
    flat_permissions = []
    for p in permissions:
        if isinstance(p, list):
            flat_permissions.extend(p)
        else:
            flat_permissions.append(p)
    
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = set()

        # Gather permissions from all user roles
        for role in current_user.roles:
            if role.permissions:
                for perm in role.permissions:
                    if isinstance(perm, str):
                        user_permissions.add(perm)

        # Wildcard permission grants all access
        if "*" in user_permissions:
            return current_user

        # Check if user has any of the required permissions
        has_any = False
        for p in flat_permissions:
            if p in user_permissions or f"{p.split(':')[0]}:*" in user_permissions:
                has_any = True
                break

        if not has_any:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing one of required permissions: {', '.join(permissions)}"
            )

        return current_user

    return permission_checker


class RateLimiter:
    """Thread-safe rate limiter with periodic cleanup for API endpoints."""

    def __init__(self, requests_per_minute: int = 60, cleanup_interval: int = 300):
        self.requests_per_minute = requests_per_minute
        self.requests: dict = {}
        self._lock = __import__('threading').Lock()
        self._last_cleanup = datetime.utcnow()
        self._cleanup_interval = cleanup_interval  # seconds

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leak."""
        now = datetime.utcnow()
        if (now - self._last_cleanup).seconds < self._cleanup_interval:
            return

        cutoff = now - timedelta(minutes=2)
        with self._lock:
            keys_to_remove = []
            for ip, timestamps in self.requests.items():
                self.requests[ip] = [t for t in timestamps if t > cutoff]
                if not self.requests[ip]:
                    keys_to_remove.append(ip)
            for key in keys_to_remove:
                del self.requests[key]
            self._last_cleanup = now

    async def __call__(self, request: Request):
        # Periodic cleanup
        self._cleanup_old_entries()

        # Get real client IP (handle proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else request.client.host

        current_time = datetime.utcnow()
        cutoff = current_time - timedelta(minutes=1)

        with self._lock:
            if client_ip not in self.requests:
                self.requests[client_ip] = []

            # Clean old requests for this IP
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > cutoff
            ]

            if len(self.requests[client_ip]) >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later."
                )

            self.requests[client_ip].append(current_time)


rate_limiter = RateLimiter()
