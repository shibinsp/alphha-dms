"""Access Request API endpoints"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db, get_current_user
from app.models import (
    User, Document, AccessRequest, DocumentPermission,
    AccessRequestStatus, RequestedPermission, PermissionLevel
)
from app.schemas.access_request import (
    AccessRequestCreate, AccessRequestResponse, AccessRequestAskReason,
    AccessRequestUpdate, AccessRequestOut
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


def map_requested_to_permission(requested: RequestedPermission) -> PermissionLevel:
    """Map requested permission to PermissionLevel"""
    mapping = {
        RequestedPermission.VIEW: PermissionLevel.VIEWER_NO_DOWNLOAD,
        RequestedPermission.DOWNLOAD: PermissionLevel.VIEWER_DOWNLOAD,
        RequestedPermission.EDIT: PermissionLevel.EDITOR,
    }
    return mapping[requested]


@router.post("", response_model=AccessRequestOut, status_code=status.HTTP_201_CREATED)
def create_access_request(
    request: AccessRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request access to a document"""
    document = db.query(Document).filter(
        Document.id == request.document_id,
        Document.tenant_id == current_user.tenant_id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user already has access
    existing_permission = db.query(DocumentPermission).filter(
        DocumentPermission.document_id == document.id,
        DocumentPermission.user_id == current_user.id,
        DocumentPermission.revoked == False
    ).first()
    if existing_permission:
        raise HTTPException(status_code=400, detail="You already have access to this document")

    # Check for pending request
    pending = db.query(AccessRequest).filter(
        AccessRequest.document_id == document.id,
        AccessRequest.requester_id == current_user.id,
        AccessRequest.status.in_([AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED])
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="You already have a pending request for this document")

    access_request = AccessRequest(
        document_id=document.id,
        tenant_id=current_user.tenant_id,
        requester_id=current_user.id,
        requested_permission=request.requested_permission,
        reason=request.reason,
        owner_id=document.created_by,
        status=AccessRequestStatus.PENDING
    )
    db.add(access_request)
    db.commit()
    db.refresh(access_request)

    # Notify document owner only
    notification_service = NotificationService(db)
    requester_name = current_user.full_name or current_user.email
    notification_service.notify_access_requested(
        tenant_id=current_user.tenant_id,
        owner_id=document.created_by,
        document_id=document.id,
        document_title=document.title,
        requester_name=requester_name
    )

    return access_request


@router.get("/my-requests", response_model=List[AccessRequestOut])
def get_my_requests(
    status_filter: Optional[AccessRequestStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get access requests I've made"""
    query = db.query(AccessRequest).filter(
        AccessRequest.requester_id == current_user.id,
        AccessRequest.tenant_id == current_user.tenant_id
    )
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    return query.order_by(AccessRequest.created_at.desc()).all()


@router.get("/pending", response_model=List[AccessRequestOut])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending access requests for documents I own or all (for admin/manager)"""
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin_or_manager = any(r in ['admin', 'super_admin', 'manager'] for r in user_roles)
    
    query = db.query(AccessRequest).filter(
        AccessRequest.tenant_id == current_user.tenant_id,
        AccessRequest.status.in_([AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED])
    )
    
    # Admin/Manager can see all pending requests, others only their own documents
    if not is_admin_or_manager:
        query = query.filter(AccessRequest.owner_id == current_user.id)
    
    return query.order_by(AccessRequest.created_at.desc()).all()


@router.get("/processed", response_model=List[AccessRequestOut])
def get_processed_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get processed (approved/rejected) access requests for documents I own"""
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin_or_manager = any(r in ['admin', 'super_admin', 'manager'] for r in user_roles)
    
    query = db.query(AccessRequest).filter(
        AccessRequest.tenant_id == current_user.tenant_id,
        AccessRequest.status.in_([AccessRequestStatus.APPROVED, AccessRequestStatus.REJECTED])
    )
    
    if not is_admin_or_manager:
        query = query.filter(AccessRequest.owner_id == current_user.id)
    
    return query.order_by(AccessRequest.responded_at.desc()).all()


@router.get("/{request_id}", response_model=AccessRequestOut)
def get_access_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific access request"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Only requester or owner can view
    if access_request.requester_id != current_user.id and access_request.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return access_request


@router.post("/{request_id}/approve", response_model=AccessRequestOut)
def approve_request(
    request_id: str,
    response: AccessRequestResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve an access request (owner/admin/manager can approve)"""
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin_or_manager = any(r in ['admin', 'super_admin', 'manager'] for r in user_roles)
    
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")
    
    # Check authorization: owner or admin/manager
    if access_request.owner_id != current_user.id and not is_admin_or_manager:
        raise HTTPException(status_code=403, detail="Not authorized to approve this request")

    if access_request.status not in [AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED]:
        raise HTTPException(status_code=400, detail="Request already processed")

    # Determine permission level
    granted = response.granted_permission or map_requested_to_permission(access_request.requested_permission)

    # Create document permission
    permission = DocumentPermission(
        document_id=access_request.document_id,
        tenant_id=access_request.tenant_id,
        user_id=access_request.requester_id,
        permission_level=granted,
        granted_by=current_user.id
    )
    db.add(permission)

    # Update request
    access_request.status = AccessRequestStatus.APPROVED
    access_request.granted_permission = granted
    access_request.owner_comment = response.comment
    access_request.responded_at = datetime.utcnow()

    db.commit()
    db.refresh(access_request)

    # Notify requester
    document = db.query(Document).filter(Document.id == access_request.document_id).first()
    notification_service = NotificationService(db)
    notification_service.notify_access_approved(
        tenant_id=access_request.tenant_id,
        requester_id=access_request.requester_id,
        document_id=access_request.document_id,
        document_title=document.title if document else "Document"
    )

    return access_request


@router.post("/{request_id}/reject", response_model=AccessRequestOut)
def reject_request(
    request_id: str,
    response: AccessRequestResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an access request (owner/admin/manager can reject)"""
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin_or_manager = any(r in ['admin', 'super_admin', 'manager'] for r in user_roles)
    
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")
    
    # Check authorization: owner or admin/manager
    if access_request.owner_id != current_user.id and not is_admin_or_manager:
        raise HTTPException(status_code=403, detail="Not authorized to reject this request")

    if access_request.status not in [AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED]:
        raise HTTPException(status_code=400, detail="Request already processed")

    access_request.status = AccessRequestStatus.REJECTED
    access_request.owner_comment = response.comment
    access_request.responded_at = datetime.utcnow()

    db.commit()
    db.refresh(access_request)

    # Notify requester
    document = db.query(Document).filter(Document.id == access_request.document_id).first()
    notification_service = NotificationService(db)
    notification_service.notify_access_rejected(
        tenant_id=access_request.tenant_id,
        requester_id=access_request.requester_id,
        document_id=access_request.document_id,
        document_title=document.title if document else "Document"
    )

    return access_request


@router.post("/{request_id}/ask-reason", response_model=AccessRequestOut)
def ask_for_reason(
    request_id: str,
    request: AccessRequestAskReason,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask requester to provide a reason"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.owner_id == current_user.id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if access_request.status != AccessRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only ask reason for pending requests")

    access_request.status = AccessRequestStatus.REASON_REQUESTED
    access_request.owner_comment = request.comment

    db.commit()
    db.refresh(access_request)
    return access_request


@router.patch("/{request_id}", response_model=AccessRequestOut)
def update_request(
    request_id: str,
    update: AccessRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update access request (requester can add reason)"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.requester_id == current_user.id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if access_request.status not in [AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED]:
        raise HTTPException(status_code=400, detail="Cannot update processed request")

    if update.reason:
        access_request.reason = update.reason
        if access_request.status == AccessRequestStatus.REASON_REQUESTED:
            access_request.status = AccessRequestStatus.PENDING

    db.commit()
    db.refresh(access_request)
    return access_request


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel my access request"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.requester_id == current_user.id,
        AccessRequest.tenant_id == current_user.tenant_id
    ).first()
    if not access_request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if access_request.status not in [AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED]:
        raise HTTPException(status_code=400, detail="Cannot cancel processed request")

    db.delete(access_request)
    db.commit()
