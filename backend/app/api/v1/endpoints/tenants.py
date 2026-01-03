from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantConfigResponse
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()


@router.get("/current", response_model=TenantConfigResponse)
async def get_current_tenant_config(
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Get current tenant configuration (for branding, etc.).
    """
    return TenantConfigResponse(
        name=tenant.name,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color or "#1E3A5F"
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tenant details (requires super admin or tenant admin).
    """
    # Check if user is super admin or belongs to the tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this tenant"
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    request: Request,
    tenant_id: str,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update tenant (requires super admin or tenant admin with admin.tenants permission).
    """
    # Check authorization
    if not current_user.is_superuser:
        if current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        if not current_user.has_permission("admin.tenants"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing admin.tenants permission"
            )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Update fields
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)

    return tenant


# Super admin only endpoints
@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tenants (super admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    tenants = db.query(Tenant).all()
    return tenants


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new tenant (super admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    # Check subdomain uniqueness
    existing = db.query(Tenant).filter(Tenant.subdomain == tenant_data.subdomain).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subdomain already exists"
        )

    tenant = Tenant(
        name=tenant_data.name,
        subdomain=tenant_data.subdomain,
        logo_url=tenant_data.logo_url,
        primary_color=tenant_data.primary_color,
        license_key=tenant_data.license_key,
        license_expires=tenant_data.license_expires,
        config=tenant_data.config
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant
