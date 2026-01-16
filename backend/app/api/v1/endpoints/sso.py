"""SSO Authentication (OIDC/SAML) Module"""
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import secrets
import base64
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User, Tenant, Session as UserSession
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["SSO Authentication"])

# In-memory state storage (use Redis in production)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


@router.get("/oidc/login")
async def oidc_login(tenant_subdomain: str, redirect_uri: Optional[str] = None):
    """Initiate OIDC login flow."""
    if not settings.SSO_ENABLED or settings.SSO_PROVIDER != "oidc":
        raise HTTPException(400, "OIDC SSO not enabled")
    
    if not settings.OIDC_ISSUER_URL or not settings.OIDC_CLIENT_ID:
        raise HTTPException(500, "OIDC not configured")
    
    # Generate state and PKCE
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    
    _oauth_states[state] = {
        "tenant_subdomain": tenant_subdomain,
        "redirect_uri": redirect_uri or "http://localhost:7000",
        "verifier": verifier,
        "created_at": datetime.utcnow()
    }
    
    # Build authorization URL
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256"
    }
    
    auth_url = f"{settings.OIDC_ISSUER_URL}/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle OIDC callback."""
    if state not in _oauth_states:
        raise HTTPException(400, "Invalid state")
    
    state_data = _oauth_states.pop(state)
    
    # Check state expiry (5 minutes)
    if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=5):
        raise HTTPException(400, "State expired")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{settings.OIDC_ISSUER_URL}/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.OIDC_CLIENT_ID,
                "client_secret": settings.OIDC_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.OIDC_REDIRECT_URI,
                "code_verifier": state_data["verifier"]
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(400, "Token exchange failed")
        
        tokens = token_response.json()
        
        # Get user info
        userinfo_response = await client.get(
            f"{settings.OIDC_ISSUER_URL}/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(400, "Failed to get user info")
        
        userinfo = userinfo_response.json()
    
    # Find or create user
    tenant = db.query(Tenant).filter(
        Tenant.subdomain == state_data["tenant_subdomain"]
    ).first()
    
    if not tenant:
        raise HTTPException(400, "Invalid tenant")
    
    email = userinfo.get("email")
    if not email:
        raise HTTPException(400, "Email not provided by IdP")
    
    user = db.query(User).filter(
        User.email == email,
        User.tenant_id == tenant.id
    ).first()
    
    if not user:
        # Auto-provision user from SSO
        user = User(
            email=email,
            full_name=userinfo.get("name", email.split("@")[0]),
            tenant_id=tenant.id,
            is_active=True,
            sso_provider="oidc",
            sso_subject_id=userinfo.get("sub"),
            password_hash=""  # No password for SSO users
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create session tokens
    auth_service = AuthService(db)
    tokens = auth_service.create_tokens(
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    # Redirect to frontend with tokens
    redirect_url = f"{state_data['redirect_uri']}?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    return RedirectResponse(redirect_url)


@router.get("/saml/login")
async def saml_login(tenant_subdomain: str):
    """Initiate SAML login flow."""
    if not settings.SSO_ENABLED or settings.SSO_PROVIDER != "saml":
        raise HTTPException(400, "SAML SSO not enabled")
    
    # SAML implementation would use python3-saml library
    # This is a placeholder for the SAML flow
    raise HTTPException(501, "SAML implementation requires python3-saml library")


@router.post("/saml/acs")
async def saml_acs(request: Request, db: Session = Depends(get_db)):
    """SAML Assertion Consumer Service endpoint."""
    if not settings.SSO_ENABLED or settings.SSO_PROVIDER != "saml":
        raise HTTPException(400, "SAML SSO not enabled")
    
    # SAML assertion processing would go here
    raise HTTPException(501, "SAML implementation requires python3-saml library")


@router.get("/sso/status")
async def sso_status():
    """Get SSO configuration status."""
    return {
        "sso_enabled": settings.SSO_ENABLED,
        "provider": settings.SSO_PROVIDER if settings.SSO_ENABLED else None,
        "oidc_configured": bool(settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID),
        "saml_configured": bool(settings.SAML_IDP_METADATA_URL)
    }
