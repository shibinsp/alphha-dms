"""Approval Workflow API Endpoints - M05"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import (
    get_current_user,
    get_current_tenant_id,
    require_permissions,
)
from app.models.user import User
from app.schemas.workflow import (
    ApprovalWorkflowCreate,
    ApprovalWorkflowUpdate,
    ApprovalWorkflowResponse,
    ApprovalRequestResponse,
    SubmitApprovalRequest,
    ApproveRejectRequest,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Approval Workflows"])


# Workflow Templates
@router.post("/", response_model=ApprovalWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: ApprovalWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["workflows:create"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a new approval workflow template"""
    service = WorkflowService(db)
    return service.create_workflow(tenant_id, current_user.id, data)


@router.get("/", response_model=List[ApprovalWorkflowResponse])
async def list_workflows(
    is_active: Optional[bool] = None,
    document_type_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["workflows:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List all approval workflows"""
    service = WorkflowService(db)
    return service.list_workflows(tenant_id, is_active, document_type_id)


@router.get("/{workflow_id}", response_model=ApprovalWorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["workflows:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a specific workflow by ID"""
    service = WorkflowService(db)
    workflow = service.get_workflow(workflow_id, tenant_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=ApprovalWorkflowResponse)
async def update_workflow(
    workflow_id: str,
    data: ApprovalWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["workflows:update"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a workflow"""
    service = WorkflowService(db)
    return service.update_workflow(workflow_id, tenant_id, current_user.id, data)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["workflows:delete"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a workflow"""
    service = WorkflowService(db)
    service.delete_workflow(workflow_id, tenant_id, current_user.id)


# Approval Requests
@router.post("/documents/{document_id}/submit", response_model=ApprovalRequestResponse)
async def submit_for_approval(
    document_id: str,
    data: SubmitApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Submit a document for approval"""
    service = WorkflowService(db)
    return service.submit_for_approval(document_id, tenant_id, current_user.id, data)


@router.get("/requests/pending", response_model=List[ApprovalRequestResponse])
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get pending approval requests for current user"""
    service = WorkflowService(db)
    role_ids = [role.id for role in current_user.roles] if current_user.roles else []
    return service.get_pending_approvals(tenant_id, current_user.id, role_ids)


@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get an approval request by ID"""
    service = WorkflowService(db)
    request = service.get_approval_request(request_id, tenant_id)
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return request


@router.post("/requests/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request_id: str,
    data: ApproveRejectRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:approve"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Approve an approval request"""
    service = WorkflowService(db)
    comments = data.comments if data else None
    return service.approve(request_id, tenant_id, current_user.id, comments)


@router.post("/requests/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request_id: str,
    data: ApproveRejectRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:approve"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Reject an approval request"""
    service = WorkflowService(db)
    comments = data.comments if data else None
    return service.reject(request_id, tenant_id, current_user.id, comments)


@router.post("/requests/{request_id}/cancel", response_model=ApprovalRequestResponse)
async def cancel_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Cancel an approval request (by requester only)"""
    service = WorkflowService(db)
    return service.cancel(request_id, tenant_id, current_user.id)
