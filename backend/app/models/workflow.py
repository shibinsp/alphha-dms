"""Approval Workflow Models - M05"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowType(str, enum.Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ApprovalWorkflow(Base):
    """Workflow template definition"""
    __tablename__ = "approval_workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    workflow_type = Column(Enum(WorkflowType), default=WorkflowType.SEQUENTIAL, nullable=False)

    # Which document types this workflow applies to
    document_type_id = Column(String(36), ForeignKey("document_types.id"), nullable=True)

    # Auto-trigger conditions
    auto_trigger_on_upload = Column(Boolean, default=False)
    auto_trigger_on_status = Column(String(50), nullable=True)  # e.g., "REVIEW"

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"))

    # Relationships
    tenant = relationship("Tenant", backref="workflows")
    document_type = relationship("DocumentType", backref="workflows")
    creator = relationship("User", foreign_keys=[created_by])
    steps = relationship("ApprovalStep", back_populates="workflow", order_by="ApprovalStep.step_order", cascade="all, delete-orphan")


class ApprovalStep(Base):
    """Individual step in a workflow"""
    __tablename__ = "approval_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("approval_workflows.id"), nullable=False)

    step_order = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Who can approve this step
    approver_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # Specific user
    approver_role_id = Column(String(36), ForeignKey("roles.id"), nullable=True)  # Any user with this role
    approver_department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)  # Department head

    # Step configuration
    required_approvals = Column(Integer, default=1)  # For parallel workflows
    allow_delegation = Column(Boolean, default=False)
    auto_approve_days = Column(Integer, nullable=True)  # Auto-approve after N days

    # Notifications
    notify_on_pending = Column(Boolean, default=True)
    reminder_days = Column(Integer, default=3)  # Send reminder after N days

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("ApprovalWorkflow", back_populates="steps")
    approver_user = relationship("User", foreign_keys=[approver_user_id])
    approver_role = relationship("Role", foreign_keys=[approver_role_id])


class ApprovalRequest(Base):
    """Active approval request instance"""
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    workflow_id = Column(String(36), ForeignKey("approval_workflows.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)

    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    current_step = Column(Integer, default=1)

    # Request metadata
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)

    completed_at = Column(DateTime, nullable=True)
    final_decision_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    final_comments = Column(Text)

    # Priority and deadline
    priority = Column(String(20), default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    deadline = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="approval_requests")
    workflow = relationship("ApprovalWorkflow", backref="requests")
    document = relationship("Document", backref="approval_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    final_approver = relationship("User", foreign_keys=[final_decision_by])
    actions = relationship("ApprovalAction", back_populates="request", cascade="all, delete-orphan")


class ApprovalAction(Base):
    """Individual approval/rejection action"""
    __tablename__ = "approval_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("approval_requests.id"), nullable=False)
    step_id = Column(String(36), ForeignKey("approval_steps.id"), nullable=False)

    action = Column(Enum(StepStatus), nullable=False)
    comments = Column(Text)

    # Who took the action
    acted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    delegated_from = Column(String(36), ForeignKey("users.id"), nullable=True)  # If delegated

    acted_at = Column(DateTime, default=datetime.utcnow)

    # For parallel workflows - track individual approvals
    is_final_for_step = Column(Boolean, default=True)

    # Relationships
    request = relationship("ApprovalRequest", back_populates="actions")
    step = relationship("ApprovalStep", backref="actions")
    actor = relationship("User", foreign_keys=[acted_by])
    delegator = relationship("User", foreign_keys=[delegated_from])
