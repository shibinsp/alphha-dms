"""Analytics schemas for M15"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.analytics import MetricType, TimeGranularity


class MetricBase(BaseModel):
    metric_type: MetricType
    granularity: TimeGranularity
    period_start: datetime
    period_end: datetime
    value: float
    count: int = 0
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class MetricResponse(MetricBase):
    id: str
    tenant_id: str
    computed_at: datetime

    class Config:
        from_attributes = True


class DashboardWidgetBase(BaseModel):
    widget_type: str
    title: str
    config: Dict[str, Any] = Field(default_factory=dict)
    position_x: int = 0
    position_y: int = 0
    width: int = 4
    height: int = 3


class DashboardWidgetCreate(DashboardWidgetBase):
    pass


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_visible: Optional[str] = None


class DashboardWidgetResponse(DashboardWidgetBase):
    id: str
    tenant_id: str
    user_id: Optional[str]
    is_visible: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceAlertBase(BaseModel):
    alert_type: str
    severity: str
    title: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class ComplianceAlertCreate(ComplianceAlertBase):
    pass


class ComplianceAlertResponse(ComplianceAlertBase):
    id: str
    tenant_id: str
    status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    pass


class AlertResolve(BaseModel):
    resolution_note: Optional[str] = None


class ReportScheduleBase(BaseModel):
    name: str
    report_type: str
    schedule_cron: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    recipients: List[str] = Field(default_factory=list)


class ReportScheduleCreate(ReportScheduleBase):
    pass


class ReportScheduleUpdate(BaseModel):
    name: Optional[str] = None
    schedule_cron: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    recipients: Optional[List[str]] = None
    is_active: Optional[str] = None


class ReportScheduleResponse(ReportScheduleBase):
    id: str
    tenant_id: str
    created_by: str
    is_active: str
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportExecutionResponse(BaseModel):
    id: str
    schedule_id: Optional[str]
    tenant_id: str
    executed_by: Optional[str]
    report_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    file_path: Optional[str]
    file_size: Optional[int]
    row_count: Optional[int]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# Dashboard data response schemas
class DocumentStats(BaseModel):
    total_documents: int
    documents_today: int
    documents_this_week: int
    documents_this_month: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_department: Dict[str, int]


class OCRStats(BaseModel):
    total_processed: int
    pending: int
    failed: int
    avg_processing_time: float
    success_rate: float


class WorkflowStats(BaseModel):
    pending_approvals: int
    approved_today: int
    rejected_today: int
    avg_approval_time: float
    overdue_count: int


class ComplianceStats(BaseModel):
    compliance_score: float
    documents_with_pii: int
    legal_holds_active: int
    retention_expiring_soon: int
    worm_records: int


class StorageStats(BaseModel):
    total_storage_mb: float
    used_storage_mb: float
    storage_by_type: Dict[str, float]


class DashboardSummary(BaseModel):
    documents: DocumentStats
    ocr: OCRStats
    workflows: WorkflowStats
    compliance: ComplianceStats
    storage: StorageStats
    recent_activity: List[Dict[str, Any]]
    alerts: List[ComplianceAlertResponse]
