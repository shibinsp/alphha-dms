"""Compliance API Endpoints - M06 WORM, M07 Retention, M08 Legal Hold"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import (
    get_current_user,
    get_current_tenant_id,
    require_permissions,
)
from app.models.user import User
from app.models.compliance import LegalHoldStatus
from app.schemas.compliance import (
    WORMLockRequest,
    WORMRecordResponse,
    WORMExtendRequest,
    WORMVerifyResponse,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    RetentionPolicyResponse,
    PolicyExecutionLogResponse,
    ExpiringDocumentResponse,
    LegalHoldCreate,
    LegalHoldResponse,
    LegalHoldReleaseRequest,
    AddDocumentsToHoldRequest,
    EvidenceExportCreate,
    EvidenceExportResponse,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(tags=["Compliance"])


# M06 - WORM Records
@router.post(
    "/documents/{document_id}/lock-worm",
    response_model=WORMRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["WORM Records"],
)
async def lock_document_worm(
    document_id: str,
    data: WORMLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:lock"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Lock a document with WORM protection"""
    service = ComplianceService(db)
    return service.lock_document_worm(document_id, tenant_id, current_user.id, data)


@router.get(
    "/documents/{document_id}/verify-integrity",
    response_model=WORMVerifyResponse,
    tags=["WORM Records"],
)
async def verify_document_integrity(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Verify WORM document integrity"""
    service = ComplianceService(db)
    return service.verify_worm_integrity(document_id, tenant_id)


@router.post(
    "/documents/{document_id}/extend-worm",
    response_model=WORMRecordResponse,
    tags=["WORM Records"],
)
async def extend_worm_retention(
    document_id: str,
    data: WORMExtendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:lock"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Extend WORM retention period (cannot shorten)"""
    service = ComplianceService(db)
    return service.extend_worm_retention(
        document_id, tenant_id, current_user.id, data.new_retention_until, data.reason
    )


# M07 - Retention Policies
@router.post(
    "/retention-policies",
    response_model=RetentionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Retention Policies"],
)
async def create_retention_policy(
    data: RetentionPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["settings:update"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a retention policy"""
    service = ComplianceService(db)
    return service.create_retention_policy(tenant_id, current_user.id, data)


@router.get(
    "/retention-policies",
    response_model=List[RetentionPolicyResponse],
    tags=["Retention Policies"],
)
async def list_retention_policies(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["settings:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List all retention policies"""
    service = ComplianceService(db)
    return service.get_retention_policies(tenant_id, is_active)


@router.put(
    "/retention-policies/{policy_id}",
    response_model=RetentionPolicyResponse,
    tags=["Retention Policies"],
)
async def update_retention_policy(
    policy_id: str,
    data: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["settings:update"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a retention policy"""
    service = ComplianceService(db)
    return service.update_retention_policy(policy_id, tenant_id, current_user.id, data)


@router.get(
    "/records/expiring",
    response_model=List[ExpiringDocumentResponse],
    tags=["Retention Policies"],
)
async def get_expiring_documents(
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:read"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get documents expiring within specified days"""
    service = ComplianceService(db)
    return service.get_expiring_documents(tenant_id, days_ahead)


@router.post(
    "/retention-policies/{policy_id}/execute",
    response_model=List[PolicyExecutionLogResponse],
    tags=["Retention Policies"],
)
async def execute_retention_policy(
    policy_id: str,
    dry_run: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["settings:update"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Execute retention policy (dry_run=True for preview)"""
    service = ComplianceService(db)
    return service.execute_retention_policy(policy_id, tenant_id, dry_run)


# M08 - Legal Hold
@router.post(
    "/legal-holds",
    response_model=LegalHoldResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Legal Hold"],
)
async def create_legal_hold(
    data: LegalHoldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a new legal hold"""
    service = ComplianceService(db)
    return service.create_legal_hold(tenant_id, current_user.id, data)


@router.get(
    "/legal-holds",
    response_model=List[LegalHoldResponse],
    tags=["Legal Hold"],
)
async def list_legal_holds(
    status: Optional[LegalHoldStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List all legal holds"""
    service = ComplianceService(db)
    return service.get_legal_holds(tenant_id, status)


@router.get(
    "/legal-holds/{hold_id}",
    response_model=LegalHoldResponse,
    tags=["Legal Hold"],
)
async def get_legal_hold(
    hold_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a legal hold by ID"""
    service = ComplianceService(db)
    hold = service.get_legal_hold(hold_id, tenant_id)
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    return hold


@router.post(
    "/legal-holds/{hold_id}/documents",
    response_model=LegalHoldResponse,
    tags=["Legal Hold"],
)
async def add_documents_to_hold(
    hold_id: str,
    data: AddDocumentsToHoldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Add documents to a legal hold"""
    service = ComplianceService(db)
    return service.add_documents_to_hold(
        hold_id, data.document_ids, tenant_id, current_user.id
    )


@router.post(
    "/legal-holds/{hold_id}/release",
    response_model=LegalHoldResponse,
    tags=["Legal Hold"],
)
async def release_legal_hold(
    hold_id: str,
    data: LegalHoldReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Release a legal hold"""
    service = ComplianceService(db)
    return service.release_legal_hold(hold_id, tenant_id, current_user.id, data.reason)


# E-Discovery Export
@router.post(
    "/legal-holds/{hold_id}/export",
    response_model=EvidenceExportResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Legal Hold"],
)
async def create_evidence_export(
    hold_id: str,
    data: EvidenceExportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create an evidence export package"""
    service = ComplianceService(db)
    return service.create_evidence_export(hold_id, tenant_id, current_user.id, data)


@router.get(
    "/legal-holds/{hold_id}/exports/{export_id}/download",
    tags=["Legal Hold"],
)
async def download_evidence_export(
    hold_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["documents:legal_hold"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Download an evidence export package"""
    from app.models.compliance import EvidenceExport
    import os

    export = (
        db.query(EvidenceExport)
        .filter(
            EvidenceExport.id == export_id,
            EvidenceExport.legal_hold_id == hold_id,
            EvidenceExport.tenant_id == tenant_id,
        )
        .first()
    )

    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if not export.export_path or not os.path.exists(export.export_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        export.export_path,
        media_type="application/zip",
        filename=f"{export.export_name}.zip",
    )
