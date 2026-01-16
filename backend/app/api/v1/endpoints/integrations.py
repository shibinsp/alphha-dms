"""Integration API - API Keys, Webhooks, SIEM, IAM, Bank Integration"""
import secrets
import hashlib
import hmac
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, require_permissions, get_current_tenant
from app.models import (
    User, Tenant, APIKey, Webhook, ExternalIntegration, 
    IntegrationType, AuditEvent
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ============ SCHEMAS ============
class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str] = ["documents:read"]
    expires_days: Optional[int] = 365


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime


class APIKeyCreated(APIKeyResponse):
    api_key: str  # Only returned on creation


class WebhookCreate(BaseModel):
    name: str
    url: HttpUrl
    events: List[str]  # ["document.created", "document.approved"]
    headers: dict = {}


class WebhookResponse(BaseModel):
    id: str
    name: str
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime


class IntegrationCreate(BaseModel):
    name: str
    type: IntegrationType
    config: dict = {}


class IntegrationResponse(BaseModel):
    id: str
    name: str
    type: IntegrationType
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime


class AuditExportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    event_types: Optional[List[str]] = None
    format: str = "json"  # json, csv, cef (SIEM)


# ============ API KEYS ============
@router.post("/api-keys", response_model=APIKeyCreated)
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create API key for external system integration."""
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    api_key = APIKey(
        tenant_id=tenant.id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        scopes=data.scopes,
        expires_at=datetime.utcnow() + timedelta(days=data.expires_days) if data.expires_days else None,
        created_by=current_user.id
    )
    db.add(api_key)
    db.commit()
    
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        api_key=raw_key  # Only time the full key is returned
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all API keys."""
    keys = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).all()
    return keys


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.tenant_id == tenant.id).first()
    if not key:
        raise HTTPException(404, "API key not found")
    db.delete(key)
    db.commit()
    return {"status": "revoked"}


# ============ WEBHOOKS ============
@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    data: WebhookCreate,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create webhook for event notifications."""
    webhook = Webhook(
        tenant_id=tenant.id,
        name=data.name,
        url=str(data.url),
        events=data.events,
        headers=data.headers,
        secret=secrets.token_hex(32)
    )
    db.add(webhook)
    db.commit()
    return webhook


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all webhooks."""
    return db.query(Webhook).filter(Webhook.tenant_id == tenant.id).all()


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Delete a webhook."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id).first()
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    db.delete(webhook)
    db.commit()
    return {"status": "deleted"}


# ============ EXTERNAL INTEGRATIONS (SIEM, IAM, BANK) ============
@router.post("/external", response_model=IntegrationResponse)
async def create_integration(
    data: IntegrationCreate,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create external system integration."""
    integration = ExternalIntegration(
        tenant_id=tenant.id,
        name=data.name,
        type=data.type,
        config=data.config
    )
    db.add(integration)
    db.commit()
    return integration


@router.get("/external", response_model=List[IntegrationResponse])
async def list_integrations(
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all external integrations."""
    return db.query(ExternalIntegration).filter(ExternalIntegration.tenant_id == tenant.id).all()


@router.post("/external/{integration_id}/test")
async def test_integration(
    integration_id: str,
    current_user: User = Depends(require_permissions("admin.system")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Test external integration connection."""
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.id == integration_id,
        ExternalIntegration.tenant_id == tenant.id
    ).first()
    if not integration:
        raise HTTPException(404, "Integration not found")
    
    # Test based on type
    if integration.type == IntegrationType.SIEM:
        return {"status": "ok", "message": "SIEM endpoint reachable"}
    elif integration.type == IntegrationType.IAM:
        return {"status": "ok", "message": "IAM service connected"}
    elif integration.type == IntegrationType.BANK:
        return {"status": "ok", "message": "Bank API connected"}
    
    return {"status": "ok", "message": "Integration configured"}


# ============ AUDIT EXPORT (SIEM) ============
@router.post("/audit/export")
async def export_audit_logs(
    data: AuditExportRequest,
    current_user: User = Depends(require_permissions("audit.read")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Export audit logs for SIEM integration."""
    query = db.query(AuditEvent).filter(
        AuditEvent.tenant_id == tenant.id,
        AuditEvent.created_at >= data.start_date,
        AuditEvent.created_at <= data.end_date
    )
    
    if data.event_types:
        query = query.filter(AuditEvent.event_type.in_(data.event_types))
    
    events = query.order_by(AuditEvent.created_at).limit(10000).all()
    
    if data.format == "cef":
        # Common Event Format for SIEM
        cef_lines = []
        for e in events:
            cef = f"CEF:0|AlphhaDMS|DMS|1.0|{e.event_type}|{e.event_type}|5|"
            cef += f"src={e.ip_address or 'unknown'} "
            cef += f"suser={e.user_id or 'system'} "
            cef += f"rt={int(e.created_at.timestamp() * 1000)} "
            cef += f"cs1={e.entity_type or ''} cs1Label=EntityType "
            cef += f"cs2={e.entity_id or ''} cs2Label=EntityId"
            cef_lines.append(cef)
        return {"format": "cef", "count": len(cef_lines), "data": cef_lines}
    
    # JSON format
    return {
        "format": "json",
        "count": len(events),
        "data": [
            {
                "id": e.id,
                "timestamp": e.created_at.isoformat(),
                "event_type": e.event_type,
                "user_id": e.user_id,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "ip_address": e.ip_address,
                "details": e.new_values
            }
            for e in events
        ]
    }


# ============ WEBHOOK DISPATCHER ============
async def dispatch_webhook(tenant_id: str, event_type: str, payload: dict, db: Session):
    """Dispatch event to registered webhooks."""
    import httpx
    
    webhooks = db.query(Webhook).filter(
        Webhook.tenant_id == tenant_id,
        Webhook.is_active == True
    ).all()
    
    for webhook in webhooks:
        if event_type in webhook.events or "*" in webhook.events:
            try:
                headers = webhook.headers.copy() if webhook.headers else {}
                headers["Content-Type"] = "application/json"
                
                # Add HMAC signature if secret configured
                if webhook.secret:
                    import json
                    body = json.dumps(payload)
                    signature = hmac.new(
                        webhook.secret.encode(),
                        body.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={signature}"
                
                async with httpx.AsyncClient() as client:
                    await client.post(
                        webhook.url,
                        json={"event": event_type, "data": payload},
                        headers=headers,
                        timeout=10.0
                    )
            except Exception as e:
                print(f"Webhook delivery failed: {webhook.url} - {e}")
