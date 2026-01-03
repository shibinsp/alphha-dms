"""Version Management API - Diff, Check-in/Check-out."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.models import User, Document, DocumentVersion, DocumentLock, LifecycleStatus
from app.services.audit_service import AuditService

router = APIRouter()


class CheckoutRequest(BaseModel):
    reason: Optional[str] = None


class CheckinRequest(BaseModel):
    change_reason: Optional[str] = None


class VersionDiffResponse(BaseModel):
    version_from: int
    version_to: int
    metadata_changes: dict
    file_changed: bool
    from_checksum: str
    to_checksum: str


# ============ CHECK-IN / CHECK-OUT ============
@router.post("/documents/{doc_id}/checkout")
def checkout_document(
    doc_id: str,
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check out a document for editing (locks it)."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Check if already locked
    existing_lock = db.query(DocumentLock).filter(
        DocumentLock.document_id == doc_id
    ).first()
    
    if existing_lock:
        if existing_lock.locked_by == current_user.id:
            return {"status": "already_checked_out", "locked_by": current_user.email}
        
        lock_user = db.query(User).filter(User.id == existing_lock.locked_by).first()
        raise HTTPException(
            409,
            f"Document is checked out by {lock_user.email if lock_user else 'another user'}"
        )
    
    # Check lifecycle status - can't checkout approved/archived docs
    if doc.lifecycle_status in [LifecycleStatus.APPROVED, LifecycleStatus.ARCHIVED]:
        raise HTTPException(400, f"Cannot checkout document in {doc.lifecycle_status.value} status")
    
    # Create lock
    lock = DocumentLock(
        document_id=doc_id,
        locked_by=current_user.id,
        reason=data.reason
    )
    db.add(lock)
    
    # Log audit
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="DOCUMENT_CHECKOUT",
        resource_type="document",
        resource_id=doc_id,
        details={"reason": data.reason}
    )
    
    db.commit()
    return {"status": "checked_out", "locked_by": current_user.email, "locked_at": lock.locked_at}


@router.post("/documents/{doc_id}/checkin")
def checkin_document(
    doc_id: str,
    data: CheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check in a document (releases lock)."""
    lock = db.query(DocumentLock).filter(
        DocumentLock.document_id == doc_id
    ).first()
    
    if not lock:
        return {"status": "not_checked_out"}
    
    # Only lock holder or admin can check in
    if lock.locked_by != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Only the lock holder can check in this document")
    
    db.delete(lock)
    
    # Log audit
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="DOCUMENT_CHECKIN",
        resource_type="document",
        resource_id=doc_id,
        details={"change_reason": data.change_reason}
    )
    
    db.commit()
    return {"status": "checked_in"}


@router.get("/documents/{doc_id}/lock-status")
def get_lock_status(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document lock status."""
    lock = db.query(DocumentLock).filter(
        DocumentLock.document_id == doc_id
    ).first()
    
    if not lock:
        return {"is_locked": False}
    
    lock_user = db.query(User).filter(User.id == lock.locked_by).first()
    return {
        "is_locked": True,
        "locked_by": lock_user.email if lock_user else None,
        "locked_by_id": lock.locked_by,
        "locked_at": lock.locked_at,
        "reason": lock.reason,
        "is_mine": lock.locked_by == current_user.id
    }


@router.delete("/documents/{doc_id}/lock")
def force_unlock(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Force unlock a document (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    lock = db.query(DocumentLock).filter(
        DocumentLock.document_id == doc_id
    ).first()
    
    if not lock:
        return {"status": "not_locked"}
    
    db.delete(lock)
    
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="DOCUMENT_FORCE_UNLOCK",
        resource_type="document",
        resource_id=doc_id,
        details={"previous_holder": lock.locked_by}
    )
    
    db.commit()
    return {"status": "unlocked"}


# ============ VERSION DIFF ============
@router.get("/documents/{doc_id}/versions/{v1}/diff/{v2}", response_model=VersionDiffResponse)
def get_version_diff(
    doc_id: str,
    v1: int,
    v2: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare two versions of a document."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    version1 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id,
        DocumentVersion.version_number == v1
    ).first()
    
    version2 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id,
        DocumentVersion.version_number == v2
    ).first()
    
    if not version1 or not version2:
        raise HTTPException(404, "Version not found")
    
    # Compare metadata
    meta1 = version1.metadata_snapshot or {}
    meta2 = version2.metadata_snapshot or {}
    
    changes = {}
    all_keys = set(meta1.keys()) | set(meta2.keys())
    
    for key in all_keys:
        old_val = meta1.get(key)
        new_val = meta2.get(key)
        if old_val != new_val:
            changes[key] = {"from": old_val, "to": new_val}
    
    return VersionDiffResponse(
        version_from=v1,
        version_to=v2,
        metadata_changes=changes,
        file_changed=version1.checksum_sha256 != version2.checksum_sha256,
        from_checksum=version1.checksum_sha256,
        to_checksum=version2.checksum_sha256
    )


@router.post("/documents/{doc_id}/restore/{version_number}")
def restore_version(
    doc_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore a previous version (creates new version, doesn't overwrite)."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Check lock
    lock = db.query(DocumentLock).filter(DocumentLock.document_id == doc_id).first()
    if lock and lock.locked_by != current_user.id:
        raise HTTPException(409, "Document is checked out by another user")
    
    # Get version to restore
    old_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id,
        DocumentVersion.version_number == version_number
    ).first()
    
    if not old_version:
        raise HTTPException(404, "Version not found")
    
    # Get current max version
    max_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    new_version_num = (max_version.version_number if max_version else 0) + 1
    
    # Mark all versions as not current
    db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id
    ).update({"is_current": False})
    
    # Create new version from old
    new_version = DocumentVersion(
        document_id=doc_id,
        version_number=new_version_num,
        file_path=old_version.file_path,
        file_size=old_version.file_size,
        checksum_sha256=old_version.checksum_sha256,
        metadata_snapshot=old_version.metadata_snapshot,
        change_reason=f"Restored from version {version_number}",
        is_current=True,
        created_by=current_user.id
    )
    db.add(new_version)
    
    # Update document
    doc.current_version_id = new_version.id
    doc.file_path = old_version.file_path
    doc.file_size = old_version.file_size
    doc.checksum_sha256 = old_version.checksum_sha256
    doc.updated_by = current_user.id
    
    AuditService.log_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="VERSION_RESTORE",
        resource_type="document",
        resource_id=doc_id,
        details={"restored_from": version_number, "new_version": new_version_num}
    )
    
    db.commit()
    
    return {
        "status": "restored",
        "new_version": new_version_num,
        "restored_from": version_number
    }
