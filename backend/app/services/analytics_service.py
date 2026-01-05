"""Analytics service for M15 - Governance & Analytics Dashboard"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import (
    Document, DocumentType, Folder, Department,
    ApprovalRequest, ApprovalAction,
    WORMRecord, LegalHold, RetentionPolicy,
    DocumentPIIField, PIIAccessLog,
    AuditEvent,
    LifecycleStatus, ApprovalStatus, OCRStatus
)
from app.models.workflow import StepStatus
from app.models.analytics import (
    AnalyticsMetric, DashboardWidget, ComplianceAlert,
    ReportSchedule, ReportExecution,
    MetricType, TimeGranularity
)
from app.schemas.analytics import (
    DocumentStats, OCRStats, WorkflowStats,
    ComplianceStats, StorageStats, DashboardSummary,
    DashboardWidgetCreate, DashboardWidgetUpdate,
    ReportScheduleCreate, ReportScheduleUpdate
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(self, tenant_id: str) -> DashboardSummary:
        """Get complete dashboard summary"""
        return DashboardSummary(
            documents=self._get_document_stats(tenant_id),
            ocr=self._get_ocr_stats(tenant_id),
            workflows=self._get_workflow_stats(tenant_id),
            compliance=self._get_compliance_stats(tenant_id),
            storage=self._get_storage_stats(tenant_id),
            recent_activity=self._get_recent_activity(tenant_id),
            alerts=self._get_active_alerts(tenant_id)
        )

    def _get_document_stats(self, tenant_id: str) -> DocumentStats:
        """Get document statistics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        total = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id
        ).scalar() or 0

        today = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.created_at >= today_start
        ).scalar() or 0

        week = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.created_at >= week_start
        ).scalar() or 0

        month = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.created_at >= month_start
        ).scalar() or 0

        # By status
        status_counts = self.db.query(
            Document.lifecycle_status,
            func.count(Document.id)
        ).filter(
            Document.tenant_id == tenant_id
        ).group_by(Document.lifecycle_status).all()

        by_status = {str(s.value) if s else "unknown": c for s, c in status_counts}

        # By type
        type_counts = self.db.query(
            DocumentType.name,
            func.count(Document.id)
        ).join(DocumentType, Document.document_type_id == DocumentType.id).filter(
            Document.tenant_id == tenant_id
        ).group_by(DocumentType.name).all()

        by_type = {t or "Unknown": c for t, c in type_counts}

        # By department
        dept_counts = self.db.query(
            Department.name,
            func.count(Document.id)
        ).join(Department, Document.department_id == Department.id).filter(
            Document.tenant_id == tenant_id
        ).group_by(Department.name).all()

        by_department = {d or "Unassigned": c for d, c in dept_counts}

        return DocumentStats(
            total_documents=total,
            documents_today=today,
            documents_this_week=week,
            documents_this_month=month,
            by_status=by_status,
            by_type=by_type,
            by_department=by_department
        )

    def _get_ocr_stats(self, tenant_id: str) -> OCRStats:
        """Get OCR processing statistics"""
        total = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.ocr_status == OCRStatus.COMPLETED
        ).scalar() or 0

        pending = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.ocr_status == OCRStatus.PENDING
        ).scalar() or 0

        failed = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.ocr_status == OCRStatus.FAILED
        ).scalar() or 0

        all_docs = total + pending + failed
        success_rate = (total / all_docs * 100) if all_docs > 0 else 0

        # Calculate average OCR processing time from audit events
        avg_processing_time = self._calculate_avg_ocr_time(tenant_id)

        return OCRStats(
            total_processed=total,
            pending=pending,
            failed=failed,
            avg_processing_time=avg_processing_time,
            success_rate=round(success_rate, 2)
        )

    def _calculate_avg_ocr_time(self, tenant_id: str) -> float:
        """Calculate average OCR processing time in minutes"""
        # Get documents with completed OCR
        # We calculate time difference from document creation to last update
        # when OCR completed (approximation since we don't have ocr_completed_at)
        docs_with_ocr = self.db.query(Document).filter(
            Document.tenant_id == tenant_id,
            Document.ocr_status == OCRStatus.COMPLETED,
            Document.ocr_text.isnot(None),
        ).limit(100).all()

        if not docs_with_ocr:
            return 0.0

        total_time = 0
        count = 0
        for doc in docs_with_ocr:
            if doc.updated_at and doc.created_at:
                diff = (doc.updated_at - doc.created_at).total_seconds() / 60  # minutes
                # Only count if reasonable (less than 1 hour - exclude manual updates)
                if 0 < diff < 60:
                    total_time += diff
                    count += 1

        return round(total_time / count, 2) if count > 0 else 0.0

    def _get_workflow_stats(self, tenant_id: str) -> WorkflowStats:
        """Get workflow statistics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        pending = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        ).scalar() or 0

        approved_today = self.db.query(func.count(ApprovalAction.id)).filter(
            ApprovalAction.action == StepStatus.APPROVED,
            ApprovalAction.acted_at >= today_start
        ).scalar() or 0

        rejected_today = self.db.query(func.count(ApprovalAction.id)).filter(
            ApprovalAction.action == StepStatus.REJECTED,
            ApprovalAction.acted_at >= today_start
        ).scalar() or 0

        # Count overdue (requests older than 7 days)
        overdue_threshold = now - timedelta(days=7)
        overdue = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.created_at < overdue_threshold
        ).scalar() or 0

        # Calculate average approval time
        avg_approval_time = self._calculate_avg_approval_time(tenant_id)

        return WorkflowStats(
            pending_approvals=pending,
            approved_today=approved_today,
            rejected_today=rejected_today,
            avg_approval_time=avg_approval_time,
            overdue_count=overdue
        )

    def _calculate_avg_approval_time(self, tenant_id: str) -> float:
        """Calculate average approval time in hours"""
        # Get completed approval requests
        completed_requests = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]),
            ApprovalRequest.completed_at.isnot(None),
        ).limit(100).all()

        if not completed_requests:
            return 0.0

        total_hours = 0
        count = 0
        for req in completed_requests:
            if req.completed_at and req.created_at:
                diff = (req.completed_at - req.created_at).total_seconds() / 3600  # hours
                # Only count if reasonable (less than 30 days)
                if 0 < diff < 720:  # 720 hours = 30 days
                    total_hours += diff
                    count += 1

        return round(total_hours / count, 1) if count > 0 else 0.0

    def _get_compliance_stats(self, tenant_id: str) -> ComplianceStats:
        """Get compliance statistics"""
        # Count documents with PII - join through Document to filter by tenant
        pii_docs = self.db.query(func.count(func.distinct(DocumentPIIField.document_id))).join(
            Document, DocumentPIIField.document_id == Document.id
        ).filter(
            Document.tenant_id == tenant_id
        ).scalar() or 0

        # Active legal holds
        legal_holds = self.db.query(func.count(LegalHold.id)).filter(
            LegalHold.tenant_id == tenant_id,
            LegalHold.status == "ACTIVE"
        ).scalar() or 0

        # WORM records
        worm_count = self.db.query(func.count(WORMRecord.id)).filter(
            WORMRecord.tenant_id == tenant_id
        ).scalar() or 0

        # Retention expiring in 30 days
        expiry_threshold = datetime.utcnow() + timedelta(days=30)
        expiring = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.retention_expiry != None,
            Document.retention_expiry <= expiry_threshold
        ).scalar() or 0

        # Calculate compliance score based on multiple factors
        score = self._calculate_compliance_score(tenant_id)

        return ComplianceStats(
            compliance_score=score,
            documents_with_pii=pii_docs,
            legal_holds_active=legal_holds,
            retention_expiring_soon=expiring,
            worm_records=worm_count
        )

    def _calculate_compliance_score(self, tenant_id: str) -> float:
        """
        Calculate compliance score based on:
        - 25% Documents with retention policy
        - 25% Documents with proper classification
        - 25% PII documents correctly classified as confidential/restricted
        - 25% No overdue approvals
        """
        total_docs = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id
        ).scalar() or 0

        if total_docs == 0:
            return 100.0  # Perfect score if no documents

        scores = []

        # 1. Documents with retention policy (25%)
        docs_with_retention = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.retention_expiry.isnot(None)
        ).scalar() or 0
        retention_score = (docs_with_retention / total_docs) * 100 if total_docs > 0 else 0
        scores.append(min(retention_score, 100) * 0.25)

        # 2. Documents with proper classification (25%)
        docs_with_classification = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.classification.isnot(None)
        ).scalar() or 0
        classification_score = (docs_with_classification / total_docs) * 100 if total_docs > 0 else 0
        scores.append(min(classification_score, 100) * 0.25)

        # 3. PII documents with proper classification (25%)
        pii_doc_ids = self.db.query(func.distinct(DocumentPIIField.document_id)).join(
            Document, DocumentPIIField.document_id == Document.id
        ).filter(Document.tenant_id == tenant_id).subquery()

        pii_docs_total = self.db.query(func.count()).select_from(pii_doc_ids).scalar() or 0

        if pii_docs_total > 0:
            properly_classified_pii = self.db.query(func.count(Document.id)).filter(
                Document.tenant_id == tenant_id,
                Document.id.in_(pii_doc_ids),
                Document.classification.in_(['CONFIDENTIAL', 'RESTRICTED'])
            ).scalar() or 0
            pii_score = (properly_classified_pii / pii_docs_total) * 100
        else:
            pii_score = 100  # No PII docs means perfect score for this category
        scores.append(min(pii_score, 100) * 0.25)

        # 4. No overdue approvals (25%)
        overdue_threshold = datetime.utcnow() - timedelta(days=7)
        pending_approvals = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        ).scalar() or 0

        overdue_approvals = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.created_at < overdue_threshold
        ).scalar() or 0

        if pending_approvals > 0:
            overdue_ratio = overdue_approvals / pending_approvals
            approval_score = (1 - overdue_ratio) * 100
        else:
            approval_score = 100  # No pending = perfect score
        scores.append(min(approval_score, 100) * 0.25)

        total_score = sum(scores)
        return round(total_score, 1)

    def _get_storage_stats(self, tenant_id: str) -> StorageStats:
        """Get storage statistics"""
        # Sum file sizes
        total_size = self.db.query(func.sum(Document.file_size)).filter(
            Document.tenant_id == tenant_id
        ).scalar() or 0

        # Convert to MB
        used_mb = total_size / (1024 * 1024)

        # Group by document type
        type_storage = self.db.query(
            DocumentType.name,
            func.sum(Document.file_size)
        ).join(DocumentType, Document.document_type_id == DocumentType.id).filter(
            Document.tenant_id == tenant_id
        ).group_by(DocumentType.name).all()

        storage_by_type = {
            t or "Unknown": round(s / (1024 * 1024), 2) if s else 0
            for t, s in type_storage
        }

        return StorageStats(
            total_storage_mb=10000,  # 10GB quota
            used_storage_mb=round(used_mb, 2),
            storage_by_type=storage_by_type
        )

    def _get_recent_activity(self, tenant_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent audit events"""
        events = self.db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id
        ).order_by(AuditEvent.created_at.desc()).limit(limit).all()

        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]

    def _get_active_alerts(self, tenant_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get active compliance alerts"""
        alerts = self.db.query(ComplianceAlert).filter(
            ComplianceAlert.tenant_id == tenant_id,
            ComplianceAlert.status == "active"
        ).order_by(ComplianceAlert.created_at.desc()).limit(limit).all()

        return [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "created_at": a.created_at.isoformat()
            }
            for a in alerts
        ]

    # Widget management
    def get_user_widgets(self, tenant_id: str, user_id: str) -> List[DashboardWidget]:
        """Get user's dashboard widgets"""
        return self.db.query(DashboardWidget).filter(
            DashboardWidget.tenant_id == tenant_id,
            or_(
                DashboardWidget.user_id == user_id,
                DashboardWidget.user_id == None
            )
        ).order_by(DashboardWidget.position_y, DashboardWidget.position_x).all()

    def create_widget(
        self,
        tenant_id: str,
        user_id: str,
        data: DashboardWidgetCreate
    ) -> DashboardWidget:
        """Create a dashboard widget"""
        widget = DashboardWidget(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            **data.model_dump()
        )
        self.db.add(widget)
        self.db.commit()
        self.db.refresh(widget)
        return widget

    def update_widget(
        self,
        widget_id: str,
        data: DashboardWidgetUpdate
    ) -> Optional[DashboardWidget]:
        """Update a dashboard widget"""
        widget = self.db.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id
        ).first()

        if not widget:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(widget, field, value)

        self.db.commit()
        self.db.refresh(widget)
        return widget

    def delete_widget(self, widget_id: str) -> bool:
        """Delete a dashboard widget"""
        widget = self.db.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id
        ).first()

        if not widget:
            return False

        self.db.delete(widget)
        self.db.commit()
        return True

    # Alert management
    def create_alert(
        self,
        tenant_id: str,
        alert_type: str,
        severity: str,
        title: str,
        description: str = None,
        entity_type: str = None,
        entity_id: str = None,
        extra_data: Dict = None
    ) -> ComplianceAlert:
        """Create a compliance alert"""
        alert = ComplianceAlert(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            extra_data=extra_data or {}
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge_alert(self, alert_id: str, user_id: str) -> Optional[ComplianceAlert]:
        """Acknowledge an alert"""
        alert = self.db.query(ComplianceAlert).filter(
            ComplianceAlert.id == alert_id
        ).first()

        if not alert:
            return None

        alert.status = "acknowledged"
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[ComplianceAlert]:
        """Resolve an alert"""
        alert = self.db.query(ComplianceAlert).filter(
            ComplianceAlert.id == alert_id
        ).first()

        if not alert:
            return None

        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)
        return alert

    # Report scheduling
    def create_report_schedule(
        self,
        tenant_id: str,
        user_id: str,
        data: ReportScheduleCreate
    ) -> ReportSchedule:
        """Create a scheduled report"""
        schedule = ReportSchedule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by=user_id,
            **data.model_dump()
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_report_schedules(self, tenant_id: str) -> List[ReportSchedule]:
        """Get all report schedules for tenant"""
        return self.db.query(ReportSchedule).filter(
            ReportSchedule.tenant_id == tenant_id
        ).all()

    def execute_report(
        self,
        tenant_id: str,
        report_type: str,
        user_id: str = None,
        schedule_id: str = None
    ) -> ReportExecution:
        """Execute a report"""
        execution = ReportExecution(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            executed_by=user_id,
            report_type=report_type,
            status="running"
        )
        self.db.add(execution)
        self.db.commit()

        # In production, this would trigger a Celery task
        # For now, mark as completed
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(execution)

        return execution
