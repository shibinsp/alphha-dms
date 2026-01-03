"""PII Detection API Endpoints - M09"""
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
from app.models.pii import PIIType
from app.schemas.pii import (
    PIIPatternCreate,
    PIIPatternUpdate,
    PIIPatternResponse,
    PIIPolicyCreate,
    PIIPolicyUpdate,
    PIIPolicyResponse,
    DocumentPIIFieldResponse,
    PIIAccessLogResponse,
    PIIDetectionRequest,
    PIIDetectionResponse,
)
from app.services.pii_service import PIIService

router = APIRouter(prefix="/pii", tags=["PII Detection"])


# Pattern Management
@router.post("/patterns", response_model=PIIPatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    data: PIIPatternCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a custom PII detection pattern"""
    service = PIIService(db)
    return service.create_pattern(tenant_id, data)


@router.get("/patterns", response_model=List[PIIPatternResponse])
async def list_patterns(
    is_active: Optional[bool] = None,
    pii_type: Optional[PIIType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:view"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List all PII detection patterns"""
    service = PIIService(db)
    return service.get_patterns(tenant_id, is_active, pii_type)


@router.put("/patterns/{pattern_id}", response_model=PIIPatternResponse)
async def update_pattern(
    pattern_id: str,
    data: PIIPatternUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a PII detection pattern"""
    service = PIIService(db)
    return service.update_pattern(pattern_id, tenant_id, data)


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a PII detection pattern"""
    service = PIIService(db)
    service.delete_pattern(pattern_id, tenant_id)


@router.post("/patterns/initialize", status_code=status.HTTP_201_CREATED)
async def initialize_system_patterns(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Initialize system PII patterns for tenant"""
    service = PIIService(db)
    service.initialize_system_patterns(tenant_id)
    return {"message": "System patterns initialized"}


# Policy Management
@router.post("/policies", response_model=PIIPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PIIPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a PII handling policy"""
    service = PIIService(db)
    return service.create_policy(tenant_id, data)


@router.get("/policies", response_model=List[PIIPolicyResponse])
async def list_policies(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:view"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List all PII handling policies"""
    service = PIIService(db)
    return service.get_policies(tenant_id, is_active)


@router.put("/policies/{policy_id}", response_model=PIIPolicyResponse)
async def update_policy(
    policy_id: str,
    data: PIIPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:manage"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a PII handling policy"""
    service = PIIService(db)
    return service.update_policy(policy_id, tenant_id, data)


# Detection
@router.post("/detect", response_model=PIIDetectionResponse)
async def detect_pii(
    data: PIIDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:view"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Detect PII in provided text content"""
    service = PIIService(db)
    results = service.detect_pii(data.content, tenant_id, data.detect_types)
    return PIIDetectionResponse(total_found=len(results), results=results)


# Document PII
@router.get("/documents/{document_id}", response_model=List[DocumentPIIFieldResponse])
async def get_document_pii(
    document_id: str,
    include_unmasked: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["pii:view"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get PII fields detected in a document"""
    service = PIIService(db)
    role_ids = [role.id for role in current_user.roles] if current_user.roles else []
    results = service.get_document_pii(
        document_id, current_user.id, tenant_id, role_ids, include_unmasked
    )
    return results


# Access Logs
@router.get("/access-logs", response_model=List[PIIAccessLogResponse])
async def get_access_logs(
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["audit:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get PII access logs"""
    from app.models.pii import PIIAccessLog

    query = db.query(PIIAccessLog).filter(PIIAccessLog.tenant_id == tenant_id)
    if document_id:
        query = query.filter(PIIAccessLog.document_id == document_id)
    if user_id:
        query = query.filter(PIIAccessLog.accessed_by == user_id)

    return query.order_by(PIIAccessLog.accessed_at.desc()).limit(limit).all()
