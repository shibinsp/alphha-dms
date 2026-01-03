"""Document Sharing & Permissions API."""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.models import User, Document
from app.models.sharing import DocumentPermission, ShareLink, PermissionLevel, ShareLinkType
from app.services.audit_service import AuditService

router = APIRouter()


class PermissionGrant(BaseModel):
    user_id: Optional[str] = None
    role_id: Optional[str] = None
    department_id: Optional[str] = None
    permission_level: str
    expires_at: Optional[datetime] = None


class ShareLinkCreate(BaseModel):
    link_type: str = "VIEW"
    password: Optional[str] = None
    max_downloads: Optional[int] = None
    expires_in_days: Optional[int] = 7


class PermissionResponse(BaseModel):
    id: str
    document_id: str
    user_id: Optional[str]
    role_id: Optional[str]
    department_id: Optional[str]
    permission_level: str
    granted_at: datetime
    expires_at: Optional[datetime]
    granted_by_email: Optional[str] = None

    class Config:
        from_attributes = True


class ShareLinkResponse(BaseModel):
    id: str
    token: str
    link_type: str
    url: str
    expires_at: Optional[datetime]
    max_downloads: Optional[int]
    download_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ PERMISSIONS ============
@router.get("/documents/{doc_id}/permissions", response_model=List[PermissionResponse])
def list_permissions(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all permissions for a document."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    perms = db.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc_id,
        DocumentPermission.revoked == False
    ).all()
    
    result = []
    for p in perms:
        resp = PermissionResponse(
            id=p.id,
            document_id=p.document_id,
            user_id=p.user_id,
            role_id=p.role_id,
            department_id=p.department_id,
            permission_level=p.permission_level.value,
            granted_at=p.granted_at,
            expires_at=p.expires_at
        )
        if p.granter:
            resp.granted_by_email = p.granter.email
        result.append(resp)
    
    return result


@router.post("/documents/{doc_id}/permissions")
def grant_permission(
    doc_id: str,
    data: PermissionGrant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant permission to a user, role, or department."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Check if user has permission to share
    user_perm = _get_user_permission(db, doc_id, current_user)
    if user_perm not in [PermissionLevel.OWNER, PermissionLevel.CO_OWNER]:
        if doc.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "No permission to share this document")
    
    # Validate permission level
    try:
        perm_level = PermissionLevel(data.permission_level)
    except ValueError:
        raise HTTPException(400, f"Invalid permission level: {data.permission_level}")
    
    # Check at least one target
    if not any([data.user_id, data.role_id, data.department_id]):
        raise HTTPException(400, "Must specify user_id, role_id, or department_id")
    
    # Check for existing permission
    existing = db.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc_id,
        DocumentPermission.user_id == data.user_id,
        DocumentPermission.role_id == data.role_id,
        DocumentPermission.department_id == data.department_id,
        DocumentPermission.revoked == False
    ).first()
    
    if existing:
        # Update existing
        existing.permission_level = perm_level
        existing.expires_at = data.expires_at
    else:
        # Create new
        perm = DocumentPermission(
            document_id=doc_id,
            tenant_id=current_user.tenant_id,
            user_id=data.user_id,
            role_id=data.role_id,
            department_id=data.department_id,
            permission_level=perm_level,
            granted_by=current_user.id,
            expires_at=data.expires_at
        )
        db.add(perm)
    
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PERMISSION_GRANT",
        resource_type="document",
        resource_id=doc_id,
        details={
            "target_user": data.user_id,
            "target_role": data.role_id,
            "target_dept": data.department_id,
            "level": data.permission_level
        }
    )
    
    db.commit()
    return {"status": "granted", "permission_level": data.permission_level}


@router.delete("/documents/{doc_id}/permissions/{perm_id}")
def revoke_permission(
    doc_id: str,
    perm_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a permission."""
    perm = db.query(DocumentPermission).filter(
        DocumentPermission.id == perm_id,
        DocumentPermission.document_id == doc_id
    ).first()
    
    if not perm:
        raise HTTPException(404, "Permission not found")
    
    # Check authorization
    user_perm = _get_user_permission(db, doc_id, current_user)
    if user_perm != PermissionLevel.OWNER:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "Only owner can revoke permissions")
    
    perm.revoked = True
    perm.revoked_at = datetime.utcnow()
    perm.revoked_by = current_user.id
    
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PERMISSION_REVOKE",
        resource_type="document",
        resource_id=doc_id,
        details={"permission_id": perm_id}
    )
    
    db.commit()
    return {"status": "revoked"}


@router.get("/documents/{doc_id}/my-permission")
def get_my_permission(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's effective permission on a document."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    perm = _get_user_permission(db, doc_id, current_user)
    
    # Check if owner
    if doc.created_by == current_user.id:
        perm = PermissionLevel.OWNER
    
    return {
        "permission_level": perm.value if perm else PermissionLevel.NO_ACCESS.value,
        "can_view": perm not in [PermissionLevel.NO_ACCESS, None],
        "can_download": perm in [PermissionLevel.OWNER, PermissionLevel.CO_OWNER, PermissionLevel.EDITOR, PermissionLevel.VIEWER_DOWNLOAD],
        "can_edit": perm in [PermissionLevel.OWNER, PermissionLevel.CO_OWNER, PermissionLevel.EDITOR],
        "can_share": perm in [PermissionLevel.OWNER, PermissionLevel.CO_OWNER],
        "can_delete": perm == PermissionLevel.OWNER,
        "is_masked": perm == PermissionLevel.RESTRICTED_MASKED
    }


# ============ SHARE LINKS ============
@router.get("/documents/{doc_id}/share-links", response_model=List[ShareLinkResponse])
def list_share_links(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all share links for a document."""
    links = db.query(ShareLink).filter(
        ShareLink.document_id == doc_id,
        ShareLink.tenant_id == current_user.tenant_id
    ).all()
    
    result = []
    for link in links:
        result.append(ShareLinkResponse(
            id=link.id,
            token=link.token,
            link_type=link.link_type.value,
            url=f"/share/{link.token}",
            expires_at=link.expires_at,
            max_downloads=link.max_downloads,
            download_count=link.download_count,
            is_active=link.is_active,
            created_at=link.created_at
        ))
    
    return result


@router.post("/documents/{doc_id}/share-links", response_model=ShareLinkResponse)
def create_share_link(
    doc_id: str,
    data: ShareLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a share link for a document."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Check permission
    user_perm = _get_user_permission(db, doc_id, current_user)
    if user_perm not in [PermissionLevel.OWNER, PermissionLevel.CO_OWNER]:
        if doc.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "No permission to create share links")
    
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)
    
    link = ShareLink(
        document_id=doc_id,
        tenant_id=current_user.tenant_id,
        link_type=ShareLinkType(data.link_type),
        max_downloads=data.max_downloads,
        expires_at=expires_at,
        created_by=current_user.id
    )
    
    if data.password:
        from app.core.security import get_password_hash
        link.password_hash = get_password_hash(data.password)
    
    db.add(link)
    
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="SHARE_LINK_CREATE",
        resource_type="document",
        resource_id=doc_id,
        details={"link_type": data.link_type}
    )
    
    db.commit()
    
    return ShareLinkResponse(
        id=link.id,
        token=link.token,
        link_type=link.link_type.value,
        url=f"/share/{link.token}",
        expires_at=link.expires_at,
        max_downloads=link.max_downloads,
        download_count=0,
        is_active=True,
        created_at=link.created_at
    )


@router.delete("/documents/{doc_id}/share-links/{link_id}")
def deactivate_share_link(
    doc_id: str,
    link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a share link."""
    link = db.query(ShareLink).filter(
        ShareLink.id == link_id,
        ShareLink.document_id == doc_id
    ).first()
    
    if not link:
        raise HTTPException(404, "Share link not found")
    
    link.is_active = False
    db.commit()
    
    return {"status": "deactivated"}


def _get_user_permission(db: Session, doc_id: str, user: User) -> Optional[PermissionLevel]:
    """Get user's effective permission level on a document."""
    # Direct user permission
    perm = db.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc_id,
        DocumentPermission.user_id == user.id,
        DocumentPermission.revoked == False
    ).first()
    
    if perm:
        if perm.expires_at and perm.expires_at < datetime.utcnow():
            return None
        return perm.permission_level
    
    # Role-based permission (check user's roles)
    from app.models import UserRole
    user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    
    for ur in user_roles:
        role_perm = db.query(DocumentPermission).filter(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.role_id == ur.role_id,
            DocumentPermission.revoked == False
        ).first()
        
        if role_perm:
            if role_perm.expires_at and role_perm.expires_at < datetime.utcnow():
                continue
            return role_perm.permission_level
    
    # Admin has full access
    if user.is_admin:
        return PermissionLevel.OWNER
    
    return None
