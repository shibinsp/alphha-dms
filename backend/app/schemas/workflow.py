"""Approval Workflow Schemas - M05"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.workflow import WorkflowType, ApprovalStatus, StepStatus


# Approval Step Schemas
class ApprovalStepBase(BaseModel):
    step_order: int
    name: str
    description: Optional[str] = None
    approver_user_id: Optional[str] = None
    approver_role_id: Optional[str] = None
    approver_department_id: Optional[str] = None
    required_approvals: int = 1
    allow_delegation: bool = False
    auto_approve_days: Optional[int] = None
    notify_on_pending: bool = True
    reminder_days: int = 3


class ApprovalStepCreate(ApprovalStepBase):
    pass


class ApprovalStepUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    approver_user_id: Optional[str] = None
    approver_role_id: Optional[str] = None
    approver_department_id: Optional[str] = None
    required_approvals: Optional[int] = None
    allow_delegation: Optional[bool] = None
    auto_approve_days: Optional[int] = None
    notify_on_pending: Optional[bool] = None
    reminder_days: Optional[int] = None


class ApprovalStepResponse(ApprovalStepBase):
    id: str
    workflow_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Approval Workflow Schemas
class ApprovalWorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    workflow_type: WorkflowType = WorkflowType.SEQUENTIAL
    document_type_id: Optional[str] = None
    auto_trigger_on_upload: bool = False
    auto_trigger_on_status: Optional[str] = None
    is_active: bool = True


class ApprovalWorkflowCreate(ApprovalWorkflowBase):
    steps: List[ApprovalStepCreate] = []


class ApprovalWorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None
    document_type_id: Optional[str] = None
    auto_trigger_on_upload: Optional[bool] = None
    auto_trigger_on_status: Optional[str] = None
    is_active: Optional[bool] = None


class ApprovalWorkflowResponse(ApprovalWorkflowBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    steps: List[ApprovalStepResponse] = []

    class Config:
        from_attributes = True


# Approval Action Schemas
class ApprovalActionBase(BaseModel):
    action: StepStatus
    comments: Optional[str] = None


class ApprovalActionCreate(ApprovalActionBase):
    pass


class ApprovalActionResponse(ApprovalActionBase):
    id: str
    request_id: str
    step_id: str
    acted_by: str
    delegated_from: Optional[str] = None
    acted_at: datetime
    is_final_for_step: bool

    class Config:
        from_attributes = True


# Approval Request Schemas
class ApprovalRequestBase(BaseModel):
    workflow_id: str
    document_id: str
    priority: str = "NORMAL"
    deadline: Optional[datetime] = None


class ApprovalRequestCreate(ApprovalRequestBase):
    pass


class DocumentSummary(BaseModel):
    id: str
    title: str
    file_name: str

    class Config:
        from_attributes = True


class WorkflowSummary(BaseModel):
    id: str
    name: str
    workflow_type: str

    class Config:
        from_attributes = True


class ApprovalRequestResponse(ApprovalRequestBase):
    id: str
    tenant_id: str
    status: ApprovalStatus
    current_step: int
    requested_by: str
    requested_at: datetime
    completed_at: Optional[datetime] = None
    final_decision_by: Optional[str] = None
    final_comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    actions: List[ApprovalActionResponse] = []
    document: Optional[DocumentSummary] = None
    workflow: Optional[WorkflowSummary] = None

    class Config:
        from_attributes = True


# Action Input Schemas
class SubmitApprovalRequest(BaseModel):
    workflow_id: Optional[str] = None
    priority: str = "NORMAL"
    deadline: Optional[datetime] = None
    comments: Optional[str] = None


class ApproveRejectRequest(BaseModel):
    comments: Optional[str] = None


class DelegateRequest(BaseModel):
    delegate_to_user_id: str
    reason: Optional[str] = None
