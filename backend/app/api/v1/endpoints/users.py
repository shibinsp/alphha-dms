from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import (
    get_current_user, get_current_tenant,
    require_permissions
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    RoleCreate, RoleUpdate, RoleResponse
)
from app.models.user import User, Role
from app.models.tenant import Tenant

router = APIRouter()


# User endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List users in tenant with pagination and filters.
    """
    query = db.query(User).filter(User.tenant_id == tenant.id)

    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return UserListResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new user in tenant.
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user, error = auth_service.create_user(
        user_data,
        tenant_id=tenant.id,
        created_by_id=current_user.id
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    audit_service.log_event(
        event_type="user.created",
        entity_type="user",
        entity_id=user.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        new_values={
            "email": user.email,
            "full_name": user.full_name,
            "roles": [r.name for r in user.roles]
        }
    )

    return user


# Role endpoints - MUST be before /{user_id} to avoid route conflict
@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List available roles."""
    roles = db.query(Role).filter(
        (Role.tenant_id == tenant.id) | (Role.tenant_id.is_(None))
    ).all()
    return roles


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant.id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Update user information.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant.id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Store old values for audit
    old_values = {
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": [r.name for r in user.roles]
    }

    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user = auth_service.update_user(user, user_data)

    audit_service.log_event(
        event_type="user.updated",
        entity_type="user",
        entity_id=user.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        old_values=old_values,
        new_values={
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "roles": [r.name for r in user.roles]
        }
    )

    return user


@router.delete("/{user_id}")
async def deactivate_user(
    request: Request,
    user_id: str,
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Deactivate user (soft delete).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant.id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )

    auth_service = AuthService(db)
    audit_service = AuditService(db)

    auth_service.deactivate_user(user)

    audit_service.log_event(
        event_type="user.deactivated",
        entity_type="user",
        entity_id=user.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": "User deactivated successfully"}


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: Request,
    role_data: RoleCreate,
    current_user: User = Depends(require_permissions("admin.roles")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new role.
    """
    audit_service = AuditService(db)

    role = Role(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions,
        tenant_id=tenant.id
    )

    db.add(role)
    db.commit()
    db.refresh(role)

    audit_service.log_event(
        event_type="role.created",
        entity_type="role",
        entity_id=role.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        new_values={
            "name": role.name,
            "permissions": role.permissions
        }
    )

    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    request: Request,
    role_id: str,
    role_data: RoleUpdate,
    current_user: User = Depends(require_permissions("admin.roles")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Update role.
    """
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.tenant_id == tenant.id
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system roles"
        )

    old_values = {
        "name": role.name,
        "permissions": role.permissions
    }

    update_data = role_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)

    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="role.updated",
        entity_type="role",
        entity_id=role.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        old_values=old_values,
        new_values={
            "name": role.name,
            "permissions": role.permissions
        }
    )

    return role


@router.post("/{user_id}/roles")
async def assign_roles(
    request: Request,
    user_id: str,
    role_ids: List[str],
    current_user: User = Depends(require_permissions("admin.users")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Assign roles to user.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant.id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    old_roles = [r.name for r in user.roles]

    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    user.roles = roles
    db.commit()

    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="user.role_assigned",
        entity_type="user",
        entity_id=user.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        old_values={"roles": old_roles},
        new_values={"roles": [r.name for r in user.roles]}
    )

    return {"message": "Roles assigned successfully"}
