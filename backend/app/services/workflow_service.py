"""Approval Workflow Service - M05"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.workflow import (
    ApprovalWorkflow,
    ApprovalStep,
    ApprovalRequest,
    ApprovalAction,
    WorkflowType,
    ApprovalStatus,
    StepStatus,
)
from app.models.document import Document, LifecycleStatus
from app.schemas.workflow import (
    ApprovalWorkflowCreate,
    ApprovalWorkflowUpdate,
    ApprovalStepCreate,
    SubmitApprovalRequest,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    # Workflow Template CRUD
    def create_workflow(
        self,
        tenant_id: str,
        user_id: str,
        data: ApprovalWorkflowCreate,
    ) -> ApprovalWorkflow:
        workflow = ApprovalWorkflow(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            workflow_type=data.workflow_type,
            document_type_id=data.document_type_id,
            auto_trigger_on_upload=data.auto_trigger_on_upload,
            auto_trigger_on_status=data.auto_trigger_on_status,
            is_active=data.is_active,
            created_by=user_id,
        )
        self.db.add(workflow)
        self.db.flush()

        # Create steps
        for step_data in data.steps:
            step = ApprovalStep(
                workflow_id=workflow.id,
                step_order=step_data.step_order,
                name=step_data.name,
                description=step_data.description,
                approver_user_id=step_data.approver_user_id,
                approver_role_id=step_data.approver_role_id,
                approver_department_id=step_data.approver_department_id,
                required_approvals=step_data.required_approvals,
                allow_delegation=step_data.allow_delegation,
                auto_approve_days=step_data.auto_approve_days,
                notify_on_pending=step_data.notify_on_pending,
                reminder_days=step_data.reminder_days,
            )
            self.db.add(step)

        self.db.commit()
        self.db.refresh(workflow)

        self.audit_service.log_event(
            event_type="WORKFLOW_CREATED",
            entity_type="workflow",
            entity_id=workflow.id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={"name": workflow.name, "type": workflow.workflow_type.value},
        )

        return workflow

    def get_workflow(self, workflow_id: str, tenant_id: str) -> Optional[ApprovalWorkflow]:
        return (
            self.db.query(ApprovalWorkflow)
            .options(joinedload(ApprovalWorkflow.steps))
            .filter(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.tenant_id == tenant_id,
            )
            .first()
        )

    def list_workflows(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None,
        document_type_id: Optional[str] = None,
    ) -> List[ApprovalWorkflow]:
        query = self.db.query(ApprovalWorkflow).filter(
            ApprovalWorkflow.tenant_id == tenant_id
        )
        if is_active is not None:
            query = query.filter(ApprovalWorkflow.is_active == is_active)
        if document_type_id:
            query = query.filter(ApprovalWorkflow.document_type_id == document_type_id)
        return query.options(joinedload(ApprovalWorkflow.steps)).all()

    def update_workflow(
        self,
        workflow_id: str,
        tenant_id: str,
        user_id: str,
        data: ApprovalWorkflowUpdate,
    ) -> ApprovalWorkflow:
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        old_values = {"name": workflow.name, "is_active": workflow.is_active}

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(workflow, field, value)

        self.db.commit()
        self.db.refresh(workflow)

        self.audit_service.log_event(
            event_type="WORKFLOW_UPDATED",
            entity_type="workflow",
            entity_id=workflow.id,
            user_id=user_id,
            tenant_id=tenant_id,
            old_values=old_values,
            new_values=data.model_dump(exclude_unset=True),
        )

        return workflow

    def delete_workflow(self, workflow_id: str, tenant_id: str, user_id: str) -> bool:
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Check if there are active approval requests
        active_requests = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.workflow_id == workflow_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
            .count()
        )
        if active_requests > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete workflow with {active_requests} active requests",
            )

        self.audit_service.log_event(
            event_type="WORKFLOW_DELETED",
            entity_type="workflow",
            entity_id=workflow.id,
            user_id=user_id,
            tenant_id=tenant_id,
            old_values={"name": workflow.name},
        )

        self.db.delete(workflow)
        self.db.commit()
        return True

    # Approval Request Operations
    def submit_for_approval(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        data: SubmitApprovalRequest,
    ) -> ApprovalRequest:
        # Verify document exists
        document = (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.tenant_id == tenant_id)
            .first()
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check for existing pending request
        existing = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.document_id == document_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Document already has a pending approval request",
            )

        # Get or create default workflow
        workflow = None
        if data.workflow_id:
            workflow = self.get_workflow(data.workflow_id, tenant_id)
            if not workflow:
                raise HTTPException(status_code=404, detail="Workflow not found")
            if not workflow.is_active:
                raise HTTPException(status_code=400, detail="Workflow is not active")
        else:
            # Find or create default workflow for this document type
            workflow = (
                self.db.query(ApprovalWorkflow)
                .filter(
                    ApprovalWorkflow.tenant_id == tenant_id,
                    ApprovalWorkflow.is_active == True,
                )
                .first()
            )
            if not workflow:
                # Create a default workflow
                workflow = ApprovalWorkflow(
                    tenant_id=tenant_id,
                    name="Default Approval",
                    description="Default single-step approval workflow",
                    workflow_type=WorkflowType.SEQUENTIAL,
                    is_active=True,
                    created_by=user_id,
                )
                self.db.add(workflow)
                self.db.flush()
                
                # Create a single step - any manager can approve
                from app.models import Role
                manager_role = self.db.query(Role).filter(
                    Role.tenant_id == tenant_id,
                    Role.name == "manager"
                ).first()
                
                step = ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=1,
                    name="Manager Approval",
                    description="Requires manager approval",
                    approver_role_id=manager_role.id if manager_role else None,
                    required_approvals=1,
                )
                self.db.add(step)

        # Create approval request
        request = ApprovalRequest(
            tenant_id=tenant_id,
            workflow_id=workflow.id,
            document_id=document_id,
            requested_by=user_id,
            priority=data.priority,
            deadline=data.deadline,
            current_step=1,
        )
        self.db.add(request)

        # Update document status to REVIEW
        document.lifecycle_status = LifecycleStatus.REVIEW
        self.db.commit()
        self.db.refresh(request)

        self.audit_service.log_event(
            event_type="APPROVAL_SUBMITTED",
            entity_type="document",
            entity_id=document_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "request_id": request.id,
                "workflow": workflow.name,
                "priority": data.priority,
            },
        )

        # Notify approvers
        from app.models import User, Role
        from app.models.user import user_roles
        requester = self.db.query(User).filter(User.id == user_id).first()
        requester_name = requester.full_name or requester.email if requester else "Someone"
        
        notified_users = set()
        
        for step in workflow.steps:
            if step.approver_user_id:
                if step.approver_user_id not in notified_users:
                    self.notification_service.notify_approval_requested(
                        tenant_id=tenant_id,
                        approver_id=step.approver_user_id,
                        document_id=document_id,
                        document_title=document.title,
                        requester=requester_name
                    )
                    notified_users.add(step.approver_user_id)
            elif step.approver_role_id:
                # Notify all users with this role
                users_with_role = self.db.query(User).join(
                    user_roles, User.id == user_roles.c.user_id
                ).filter(
                    user_roles.c.role_id == step.approver_role_id,
                    User.tenant_id == tenant_id
                ).all()
                for approver in users_with_role:
                    if approver.id not in notified_users:
                        self.notification_service.notify_approval_requested(
                            tenant_id=tenant_id,
                            approver_id=approver.id,
                            document_id=document_id,
                            document_title=document.title,
                            requester=requester_name
                        )
                        notified_users.add(approver.id)
        
        # Also notify admins/super_admins
        admin_roles = self.db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name.in_(['admin', 'super_admin'])
        ).all()
        for role in admin_roles:
            admins = self.db.query(User).join(
                user_roles, User.id == user_roles.c.user_id
            ).filter(
                user_roles.c.role_id == role.id,
                User.tenant_id == tenant_id
            ).all()
            for admin in admins:
                if admin.id not in notified_users and admin.id != user_id:
                    self.notification_service.notify_approval_requested(
                        tenant_id=tenant_id,
                        approver_id=admin.id,
                        document_id=document_id,
                        document_title=document.title,
                        requester=requester_name
                    )
                    notified_users.add(admin.id)

        return request

    def get_approval_request(
        self, request_id: str, tenant_id: str
    ) -> Optional[ApprovalRequest]:
        return (
            self.db.query(ApprovalRequest)
            .options(joinedload(ApprovalRequest.actions))
            .filter(
                ApprovalRequest.id == request_id,
                ApprovalRequest.tenant_id == tenant_id,
            )
            .first()
        )

    def get_pending_approvals(
        self,
        tenant_id: str,
        user_id: str,
        role_ids: List[str],
    ) -> List[ApprovalRequest]:
        """Get approval requests pending for a user based on current step"""
        from app.models import Role
        
        # Check if user has manager or admin role
        user_roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
        role_names = [r.name for r in user_roles]
        is_manager_or_admin = any(r in ['manager', 'admin', 'super_admin'] for r in role_names)
        
        requests = (
            self.db.query(ApprovalRequest)
            .join(ApprovalWorkflow)
            .options(
                joinedload(ApprovalRequest.workflow),
                joinedload(ApprovalRequest.document)
            )
            .filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
            .all()
        )

        pending_for_user = []
        for request in requests:
            workflow = request.workflow
            if not workflow or not workflow.steps:
                # If no workflow steps defined, managers/admins can approve
                if is_manager_or_admin:
                    pending_for_user.append(request)
                continue

            # Find current step
            current_step = None
            for step in workflow.steps:
                if step.step_order == request.current_step:
                    current_step = step
                    break

            if not current_step:
                # No step defined, managers/admins can approve
                if is_manager_or_admin:
                    pending_for_user.append(request)
                continue

            # Check if user can approve this step
            can_approve = False
            if current_step.approver_user_id == user_id:
                can_approve = True
            elif current_step.approver_role_id and current_step.approver_role_id in role_ids:
                can_approve = True
            elif not current_step.approver_user_id and not current_step.approver_role_id:
                # No specific approver set, managers/admins can approve
                can_approve = is_manager_or_admin

            if can_approve:
                pending_for_user.append(request)

        return pending_for_user

    def approve(
        self,
        request_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> ApprovalRequest:
        request = self.get_approval_request(request_id, tenant_id)
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if request.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Request is not pending")

        workflow = self.get_workflow(request.workflow_id, tenant_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Find current step
        current_step = None
        for step in workflow.steps:
            if step.step_order == request.current_step:
                current_step = step
                break

        if not current_step:
            raise HTTPException(status_code=400, detail="Current step not found")

        # Record the action
        action = ApprovalAction(
            request_id=request.id,
            step_id=current_step.id,
            action=StepStatus.APPROVED,
            comments=comments,
            acted_by=user_id,
        )
        self.db.add(action)

        # Check if this completes the workflow
        total_steps = len(workflow.steps)
        if request.current_step >= total_steps:
            # Final approval
            request.status = ApprovalStatus.APPROVED
            request.completed_at = datetime.utcnow()
            request.final_decision_by = user_id
            request.final_comments = comments

            # Update document status
            document = self.db.query(Document).filter(Document.id == request.document_id).first()
            if document:
                document.lifecycle_status = LifecycleStatus.APPROVED
        else:
            # Move to next step
            request.current_step += 1

        self.db.commit()
        self.db.refresh(request)

        self.audit_service.log_event(
            event_type="APPROVAL_APPROVED",
            entity_type="document",
            entity_id=request.document_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "request_id": request.id,
                "step": current_step.name,
                "final": request.status == ApprovalStatus.APPROVED,
            },
        )

        # Notify requester if final approval
        if request.status == ApprovalStatus.APPROVED:
            document = self.db.query(Document).filter(Document.id == request.document_id).first()
            from app.models import User
            approver = self.db.query(User).filter(User.id == user_id).first()
            approver_name = approver.full_name or approver.email if approver else "Someone"
            if document:
                self.notification_service.notify_document_approved(
                    tenant_id=tenant_id,
                    user_id=request.requested_by,
                    document_id=request.document_id,
                    document_title=document.title,
                    approver=approver_name
                )

        return request

    def reject(
        self,
        request_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> ApprovalRequest:
        request = self.get_approval_request(request_id, tenant_id)
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if request.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Request is not pending")

        workflow = self.get_workflow(request.workflow_id, tenant_id)
        current_step = None
        for step in workflow.steps:
            if step.step_order == request.current_step:
                current_step = step
                break

        # Record rejection
        action = ApprovalAction(
            request_id=request.id,
            step_id=current_step.id if current_step else None,
            action=StepStatus.REJECTED,
            comments=comments,
            acted_by=user_id,
        )
        self.db.add(action)

        request.status = ApprovalStatus.REJECTED
        request.completed_at = datetime.utcnow()
        request.final_decision_by = user_id
        request.final_comments = comments

        # Return document to DRAFT and create new version for revision
        document = self.db.query(Document).filter(Document.id == request.document_id).first()
        if document:
            old_status = document.lifecycle_status.value
            document.lifecycle_status = LifecycleStatus.DRAFT
            
            # Create new version for revision
            from app.models import DocumentVersion
            import uuid
            
            max_version = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document.id
            ).order_by(DocumentVersion.version_number.desc()).first()
            
            new_version_num = (max_version.version_number + 1) if max_version else 1
            
            # Mark previous versions as not current
            self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document.id
            ).update({"is_current": False})
            
            # Create revision version
            new_version = DocumentVersion(
                id=str(uuid.uuid4()),
                document_id=document.id,
                version_number=new_version_num,
                file_path=document.file_path,
                file_size=document.file_size,
                checksum_sha256=document.checksum_sha256,
                metadata_snapshot={"status_before": old_status, "rejection_reason": comments},
                change_reason=f"Sent back for revision: {comments or 'No reason provided'}",
                is_current=True,
                created_by=user_id
            )
            self.db.add(new_version)
            document.current_version_id = new_version.id

        self.db.commit()
        self.db.refresh(request)

        self.audit_service.log_event(
            event_type="APPROVAL_REJECTED",
            entity_type="document",
            entity_id=request.document_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "request_id": request.id,
                "comments": comments,
            },
        )

        # Notify requester
        from app.models import User
        rejector = self.db.query(User).filter(User.id == user_id).first()
        rejector_name = rejector.full_name or rejector.email if rejector else "Someone"
        if document:
            self.notification_service.notify_document_rejected(
                tenant_id=tenant_id,
                user_id=request.requested_by,
                document_id=request.document_id,
                document_title=document.title,
                rejector=rejector_name,
                reason=comments
            )

        return request

    def cancel(
        self,
        request_id: str,
        tenant_id: str,
        user_id: str,
    ) -> ApprovalRequest:
        request = self.get_approval_request(request_id, tenant_id)
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if request.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Request is not pending")

        # Only requester can cancel
        if request.requested_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the requester can cancel the request",
            )

        request.status = ApprovalStatus.CANCELLED
        request.completed_at = datetime.utcnow()

        # Return document to DRAFT
        document = self.db.query(Document).filter(Document.id == request.document_id).first()
        if document:
            document.lifecycle_status = LifecycleStatus.DRAFT

        self.db.commit()
        self.db.refresh(request)

        self.audit_service.log_event(
            event_type="APPROVAL_CANCELLED",
            entity_type="document",
            entity_id=request.document_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        return request
