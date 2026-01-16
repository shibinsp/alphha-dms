from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, rate_limiter
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.schemas.user import (
    Token, UserLogin, UserResponse,
    MFASetupResponse, MFAVerifyRequest,
    PasswordChangeRequest, RefreshTokenRequest,
    UserCreate
)
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limiter)
):
    """
    OAuth2 compatible token login.
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user, error = auth_service.authenticate_user(
        email=form_data.username,
        password=form_data.password
    )

    if error:
        # Log failed attempt
        if user:
            audit_service.log_event(
                event_type="auth.login_failed",
                entity_type="user",
                entity_id=user.id,
                user_id=user.id,
                tenant_id=user.tenant_id,
                ip_address=request.client.host,
                user_agent=request.headers.get("User-Agent"),
                metadata={"reason": error}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = auth_service.create_tokens(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    # Log successful login
    audit_service.log_event(
        event_type="auth.login",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return tokens


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limiter)
):
    """
    JSON-based login (alternative to OAuth2 form).
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user, error = auth_service.authenticate_user(
        email=login_data.email,
        password=login_data.password,
        mfa_code=login_data.mfa_code
    )

    if error:
        if user:
            audit_service.log_event(
                event_type="auth.login_failed",
                entity_type="user",
                entity_id=user.id,
                user_id=user.id,
                tenant_id=user.tenant_id,
                ip_address=request.client.host,
                user_agent=request.headers.get("User-Agent"),
                metadata={"reason": error}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )

    tokens = auth_service.create_tokens(
        user,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    audit_service.log_event(
        event_type="auth.login",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return tokens


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    from app.models import Tenant, Role
    from app.core.security import get_password_hash
    import uuid
    
    # Check if email exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get default tenant
    tenant = db.query(Tenant).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="No tenant configured")
    
    # Get viewer role as default
    viewer_role = db.query(Role).filter(
        Role.tenant_id == tenant.id,
        Role.name == "viewer"
    ).first()
    
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        tenant_id=tenant.id,
        is_active=True
    )
    if viewer_role:
        user.roles.append(viewer_role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/logout")
async def logout(
    request: Request,
    data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current session by invalidating refresh token.
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    auth_service.logout(data.refresh_token)

    audit_service.log_event(
        event_type="auth.logout",
        entity_type="user",
        entity_id=current_user.id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService(db)
    tokens = auth_service.refresh_tokens(data.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Setup MFA for current user.
    Returns secret and QR code for authenticator app.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled"
        )

    auth_service = AuthService(db)
    secret, qr_code = auth_service.setup_mfa(current_user)

    return MFASetupResponse(secret=secret, qr_code=qr_code)


@router.post("/mfa/verify")
async def verify_and_enable_mfa(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify MFA code and enable MFA for current user.
    """
    if not data.secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secret is required for MFA verification"
        )

    auth_service = AuthService(db)
    audit_service = AuditService(db)

    if not auth_service.enable_mfa(current_user, data.secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )

    audit_service.log_event(
        event_type="auth.mfa_enabled",
        entity_type="user",
        entity_id=current_user.id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": "MFA enabled successfully"}


@router.delete("/mfa")
async def disable_mfa(
    request: Request,
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable MFA for current user (requires current MFA code).
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )

    from app.core.security import verify_mfa_code
    if not verify_mfa_code(current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )

    auth_service = AuthService(db)
    audit_service = AuditService(db)

    auth_service.disable_mfa(current_user)

    audit_service.log_event(
        event_type="auth.mfa_disabled",
        entity_type="user",
        entity_id=current_user.id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": "MFA disabled successfully"}


@router.post("/password/change")
async def change_password(
    request: Request,
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for current user.
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    success, message = auth_service.change_password(
        current_user,
        data.current_password,
        data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    audit_service.log_event(
        event_type="auth.password_changed",
        entity_type="user",
        entity_id=current_user.id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": message}
