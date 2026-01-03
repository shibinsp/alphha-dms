"""Analytics models for M15 - Governance & Analytics Dashboard"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Integer,
    Float,
    Date,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class MetricType(str, enum.Enum):
    DOCUMENT_COUNT = "document_count"
    DOCUMENT_UPLOADS = "document_uploads"
    DOCUMENT_DOWNLOADS = "document_downloads"
    STORAGE_USED = "storage_used"
    ACTIVE_USERS = "active_users"
    WORKFLOW_PENDING = "workflow_pending"
    WORKFLOW_COMPLETED = "workflow_completed"
    COMPLIANCE_SCORE = "compliance_score"
    PII_DETECTED = "pii_detected"
    SEARCH_QUERIES = "search_queries"
    CHAT_SESSIONS = "chat_sessions"


class TimeGranularity(str, enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AnalyticsMetric(Base):
    """Aggregated analytics metrics"""
    __tablename__ = "analytics_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)

    metric_type = Column(Enum(MetricType), nullable=False)
    granularity = Column(Enum(TimeGranularity), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Metric values
    value = Column(Float, nullable=False, default=0)
    count = Column(Integer, nullable=False, default=0)

    # Breakdown by dimensions
    dimensions = Column(JSON, default=dict)  # e.g., {"department": "Legal", "document_type": "Contract"}

    # Metadata
    computed_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_analytics_metrics_tenant_type_period", "tenant_id", "metric_type", "period_start"),
        Index("ix_analytics_metrics_granularity", "granularity"),
    )


class DashboardWidget(Base):
    """User-customizable dashboard widgets"""
    __tablename__ = "dashboard_widgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # null = tenant default

    widget_type = Column(String(50), nullable=False)  # chart, metric, table, alert
    title = Column(String(200), nullable=False)

    # Widget configuration
    config = Column(JSON, default=dict)  # chart type, metric, filters, etc.

    # Layout
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)  # grid units
    height = Column(Integer, default=3)

    is_visible = Column(String(5), default="true")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceAlert(Base):
    """Compliance and governance alerts"""
    __tablename__ = "compliance_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)

    alert_type = Column(String(50), nullable=False)  # retention_expiry, pii_exposure, workflow_overdue
    severity = Column(String(20), nullable=False)  # critical, high, medium, low

    title = Column(String(200), nullable=False)
    description = Column(Text)

    # Related entity
    entity_type = Column(String(50))  # document, workflow, user
    entity_id = Column(String(36))

    # Status
    status = Column(String(20), default="active")  # active, acknowledged, resolved
    acknowledged_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Extra data
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])

    __table_args__ = (
        Index("ix_compliance_alerts_tenant_status", "tenant_id", "status"),
        Index("ix_compliance_alerts_severity", "severity"),
    )


class ReportSchedule(Base):
    """Scheduled report generation"""
    __tablename__ = "report_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)  # compliance, activity, storage, audit

    # Schedule (cron-like)
    schedule_cron = Column(String(100))  # e.g., "0 9 * * MON" for every Monday 9 AM

    # Report configuration
    config = Column(JSON, default=dict)  # filters, date range, format

    # Recipients
    recipients = Column(JSON, default=list)  # list of email addresses

    # Status
    is_active = Column(String(5), default="true")
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])


class ReportExecution(Base):
    """Report execution history"""
    __tablename__ = "report_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schedule_id = Column(String(36), ForeignKey("report_schedules.id"), nullable=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    executed_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    report_type = Column(String(50), nullable=False)

    # Execution details
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Result
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)

    # Relationships
    schedule = relationship("ReportSchedule", foreign_keys=[schedule_id])
    executor = relationship("User", foreign_keys=[executed_by])
