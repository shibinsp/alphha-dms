"""License Management API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, require_permissions
from app.models import User
from app.services.license_service import LicenseService
from app.schemas.entities import LicenseValidate, LicenseResponse

router = APIRouter(prefix="/license", tags=["License"])


class LicenseCreate(BaseModel):
    validity_days: int = 365
    grace_period_days: int = 30


class LicenseRenew(BaseModel):
    license_key: str
    additional_days: int = 365


@router.post("/generate")
def generate_license(
    data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Generate a new license for the current tenant (admin only)."""
    license = LicenseService.create_license(
        db=db,
        tenant_id=current_user.tenant_id,
        validity_days=data.validity_days,
        grace_period_days=data.grace_period_days
    )
    
    return {
        "license_key": license.license_key,
        "expires_at": license.expires_at,
        "grace_period_days": license.grace_period_days
    }


@router.post("/validate", response_model=LicenseResponse)
def validate_license(
    data: LicenseValidate,
    db: Session = Depends(get_db)
):
    """Validate a license key."""
    result = LicenseService.validate_license(db, data.license_key)
    return LicenseResponse(**result)


@router.post("/renew")
def renew_license(
    data: LicenseRenew,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Renew an existing license (admin only)."""
    license = LicenseService.renew_license(
        db=db,
        license_key=data.license_key,
        additional_days=data.additional_days
    )
    
    if not license:
        raise HTTPException(404, "License not found")
    
    return {
        "license_key": license.license_key,
        "expires_at": license.expires_at,
        "message": "License renewed successfully"
    }


@router.get("/status")
def get_license_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current license status for the tenant."""
    result = LicenseService.check_platform_access(db, current_user.tenant_id)
    return result


@router.get("/current")
def get_current_license(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current license details."""
    license = LicenseService.get_tenant_license(db, current_user.tenant_id)
    
    if not license:
        return {"has_license": False}
    
    validation = LicenseService.validate_license(db, license.license_key)
    
    return {
        "has_license": True,
        "license_key": license.license_key[:20] + "...",  # Partial key for security
        "expires_at": license.expires_at,
        "is_valid": validation["is_valid"],
        "days_remaining": validation["days_remaining"],
        "in_grace_period": validation["in_grace_period"],
        "message": validation["message"]
    }
