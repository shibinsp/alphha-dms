"""Analytics API endpoints for M15 - Governance & Analytics Dashboard"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.models import User, Tenant
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    DashboardSummary, DocumentStats, OCRStats, WorkflowStats,
    ComplianceStats, StorageStats,
    DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse,
    ComplianceAlertResponse, AlertAcknowledge, AlertResolve,
    ReportScheduleCreate, ReportScheduleUpdate, ReportScheduleResponse,
    ReportExecutionResponse
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get complete dashboard summary"""
    service = AnalyticsService(db)
    return service.get_dashboard_summary(tenant.id)


@router.get("/documents", response_model=DocumentStats)
def get_document_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get document statistics"""
    service = AnalyticsService(db)
    return service._get_document_stats(tenant.id)


@router.get("/ocr", response_model=OCRStats)
def get_ocr_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get OCR processing statistics"""
    service = AnalyticsService(db)
    return service._get_ocr_stats(tenant.id)


@router.get("/workflows", response_model=WorkflowStats)
def get_workflow_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get workflow statistics"""
    service = AnalyticsService(db)
    return service._get_workflow_stats(tenant.id)


@router.get("/compliance", response_model=ComplianceStats)
def get_compliance_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get compliance statistics"""
    service = AnalyticsService(db)
    return service._get_compliance_stats(tenant.id)


@router.get("/storage", response_model=StorageStats)
def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get storage statistics"""
    service = AnalyticsService(db)
    return service._get_storage_stats(tenant.id)


# Widgets
@router.get("/widgets", response_model=List[DashboardWidgetResponse])
def get_user_widgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get user's dashboard widgets"""
    service = AnalyticsService(db)
    return service.get_user_widgets(tenant.id, current_user.id)


@router.post("/widgets", response_model=DashboardWidgetResponse)
def create_widget(
    data: DashboardWidgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Create a dashboard widget"""
    service = AnalyticsService(db)
    return service.create_widget(tenant.id, current_user.id, data)


@router.put("/widgets/{widget_id}", response_model=DashboardWidgetResponse)
def update_widget(
    widget_id: str,
    data: DashboardWidgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a dashboard widget"""
    service = AnalyticsService(db)
    widget = service.update_widget(widget_id, data)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.delete("/widgets/{widget_id}")
def delete_widget(
    widget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a dashboard widget"""
    service = AnalyticsService(db)
    if not service.delete_widget(widget_id):
        raise HTTPException(status_code=404, detail="Widget not found")
    return {"message": "Widget deleted"}


# Alerts
@router.get("/alerts", response_model=List[ComplianceAlertResponse])
def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get compliance alerts"""
    service = AnalyticsService(db)
    return service._get_active_alerts(tenant.id, limit)


@router.post("/alerts/{alert_id}/acknowledge", response_model=ComplianceAlertResponse)
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an alert"""
    service = AnalyticsService(db)
    alert = service.acknowledge_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=ComplianceAlertResponse)
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve an alert"""
    service = AnalyticsService(db)
    alert = service.resolve_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# Reports
@router.get("/reports/schedules", response_model=List[ReportScheduleResponse])
def get_report_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get scheduled reports"""
    service = AnalyticsService(db)
    return service.get_report_schedules(tenant.id)


@router.post("/reports/schedules", response_model=ReportScheduleResponse)
def create_report_schedule(
    data: ReportScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Create a scheduled report"""
    service = AnalyticsService(db)
    return service.create_report_schedule(tenant.id, current_user.id, data)


@router.post("/reports/execute", response_model=ReportExecutionResponse)
def execute_report(
    report_type: str,
    schedule_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Execute a report immediately"""
    service = AnalyticsService(db)
    return service.execute_report(
        tenant.id,
        report_type,
        current_user.id,
        schedule_id
    )
