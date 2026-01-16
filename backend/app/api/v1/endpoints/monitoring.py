"""Production Monitoring & Metrics Module"""
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import threading

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.v1.dependencies import require_permissions
from app.models import User, Document, AuditEvent, Tenant

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# In-memory metrics (use Redis/Prometheus in production)
_metrics = {
    "requests": defaultdict(int),
    "latencies": defaultdict(list),
    "errors": defaultdict(int),
    "active_users": set(),
    "start_time": datetime.utcnow()
}
_metrics_lock = threading.Lock()


def track_request(endpoint: str, latency_ms: float, status_code: int):
    """Track request metrics."""
    with _metrics_lock:
        _metrics["requests"][endpoint] += 1
        _metrics["latencies"][endpoint].append(latency_ms)
        # Keep only last 1000 latencies per endpoint
        if len(_metrics["latencies"][endpoint]) > 1000:
            _metrics["latencies"][endpoint] = _metrics["latencies"][endpoint][-1000:]
        if status_code >= 400:
            _metrics["errors"][endpoint] += 1


def track_user_activity(user_id: str):
    """Track active user."""
    with _metrics_lock:
        _metrics["active_users"].add(user_id)


class MetricsMiddleware:
    """Middleware to collect request metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        status_code = 500
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_ms = (time.time() - start_time) * 1000
            path = scope.get("path", "unknown")
            track_request(path, latency_ms, status_code)


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "api": "healthy"
        }
    }


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(require_permissions("admin.system"))
):
    """Get system metrics."""
    with _metrics_lock:
        uptime = datetime.utcnow() - _metrics["start_time"]
        
        # Calculate P95 latencies
        p95_latencies = {}
        for endpoint, latencies in _metrics["latencies"].items():
            if latencies:
                sorted_latencies = sorted(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95_latencies[endpoint] = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": sum(_metrics["requests"].values()),
            "total_errors": sum(_metrics["errors"].values()),
            "active_users": len(_metrics["active_users"]),
            "requests_by_endpoint": dict(_metrics["requests"]),
            "errors_by_endpoint": dict(_metrics["errors"]),
            "p95_latency_ms": p95_latencies
        }


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_permissions("admin.system")),
    db: Session = Depends(get_db)
):
    """Get monitoring dashboard data."""
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Document statistics
    total_documents = db.query(func.count(Document.id)).scalar()
    documents_today = db.query(func.count(Document.id)).filter(
        Document.created_at >= day_ago
    ).scalar()
    documents_week = db.query(func.count(Document.id)).filter(
        Document.created_at >= week_ago
    ).scalar()
    
    # Storage usage
    total_storage = db.query(func.sum(Document.file_size)).scalar() or 0
    
    # User activity
    active_users_today = db.query(func.count(func.distinct(AuditEvent.user_id))).filter(
        AuditEvent.created_at >= day_ago
    ).scalar()
    
    # Audit events
    events_today = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.created_at >= day_ago
    ).scalar()
    
    # Security events (failed logins, access denials)
    security_events = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.created_at >= day_ago,
        AuditEvent.event_type.in_(['auth.login_failed', 'access.denied'])
    ).scalar()
    
    return {
        "timestamp": now.isoformat(),
        "documents": {
            "total": total_documents,
            "created_today": documents_today,
            "created_week": documents_week
        },
        "storage": {
            "total_bytes": total_storage,
            "total_gb": round(total_storage / (1024**3), 2)
        },
        "users": {
            "active_today": active_users_today
        },
        "audit": {
            "events_today": events_today,
            "security_events_today": security_events
        }
    }


@router.get("/alerts")
async def get_alerts(
    current_user: User = Depends(require_permissions("admin.system")),
    db: Session = Depends(get_db)
):
    """Get active system alerts."""
    alerts = []
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    
    # Check for high error rate
    with _metrics_lock:
        total_requests = sum(_metrics["requests"].values())
        total_errors = sum(_metrics["errors"].values())
        if total_requests > 100 and (total_errors / total_requests) > 0.05:
            alerts.append({
                "severity": "warning",
                "type": "high_error_rate",
                "message": f"Error rate is {(total_errors/total_requests)*100:.1f}%",
                "timestamp": now.isoformat()
            })
    
    # Check for failed login attempts
    failed_logins = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.created_at >= hour_ago,
        AuditEvent.event_type == 'auth.login_failed'
    ).scalar()
    
    if failed_logins > 10:
        alerts.append({
            "severity": "warning",
            "type": "failed_logins",
            "message": f"{failed_logins} failed login attempts in the last hour",
            "timestamp": now.isoformat()
        })
    
    # Check for large exports
    large_exports = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.created_at >= hour_ago,
        AuditEvent.event_type == 'document.exported'
    ).scalar()
    
    if large_exports > 50:
        alerts.append({
            "severity": "info",
            "type": "high_export_volume",
            "message": f"{large_exports} document exports in the last hour",
            "timestamp": now.isoformat()
        })
    
    # Check retention compliance
    from app.models import RetentionPolicy
    overdue_docs = db.query(func.count(Document.id)).filter(
        Document.retention_expiry < now,
        Document.lifecycle_status != 'PURGED',
        Document.legal_hold == False
    ).scalar()
    
    if overdue_docs > 0:
        alerts.append({
            "severity": "warning",
            "type": "retention_overdue",
            "message": f"{overdue_docs} documents past retention expiry",
            "timestamp": now.isoformat()
        })
    
    return {"alerts": alerts, "count": len(alerts)}


# Prometheus-compatible metrics endpoint
@router.get("/prometheus")
async def prometheus_metrics():
    """Export metrics in Prometheus format."""
    with _metrics_lock:
        lines = []
        
        # Request counts
        lines.append("# HELP dms_requests_total Total HTTP requests")
        lines.append("# TYPE dms_requests_total counter")
        for endpoint, count in _metrics["requests"].items():
            safe_endpoint = endpoint.replace("/", "_").replace("-", "_")
            lines.append(f'dms_requests_total{{endpoint="{endpoint}"}} {count}')
        
        # Error counts
        lines.append("# HELP dms_errors_total Total HTTP errors")
        lines.append("# TYPE dms_errors_total counter")
        for endpoint, count in _metrics["errors"].items():
            lines.append(f'dms_errors_total{{endpoint="{endpoint}"}} {count}')
        
        # Active users
        lines.append("# HELP dms_active_users Current active users")
        lines.append("# TYPE dms_active_users gauge")
        lines.append(f"dms_active_users {len(_metrics['active_users'])}")
        
        return "\n".join(lines)
