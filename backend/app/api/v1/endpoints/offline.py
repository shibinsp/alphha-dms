"""Offline/Sync API endpoints for M17 - PWA Support"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.models import User, Tenant
from app.services.offline_service import OfflineService
from app.schemas.offline import (
    DeviceRegistrationCreate, DeviceRegistrationResponse,
    SyncQueueItemCreate, SyncQueueItemResponse,
    SyncBatchRequest, SyncBatchResponse,
    SyncConflictResponse, ConflictResolution,
    OfflineDocumentCreate, OfflineDocumentResponse,
    SyncStatusResponse, DeltaSyncRequest, DeltaSyncResponse
)

router = APIRouter(prefix="/offline", tags=["Offline Sync"])


# Device management
@router.post("/devices", response_model=DeviceRegistrationResponse)
def register_device(
    data: DeviceRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Register a device for offline sync"""
    service = OfflineService(db)
    return service.register_device(tenant.id, current_user.id, data)


@router.get("/devices", response_model=List[DeviceRegistrationResponse])
def get_user_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's registered devices"""
    service = OfflineService(db)
    return service.get_user_devices(current_user.id)


@router.delete("/devices/{device_id}")
def deactivate_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a device"""
    service = OfflineService(db)
    if not service.deactivate_device(device_id, current_user.id):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device deactivated"}


# Sync operations
@router.post("/sync", response_model=SyncBatchResponse)
def sync_batch(
    data: SyncBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Sync a batch of offline changes"""
    service = OfflineService(db)
    result = service.process_sync_batch(tenant.id, current_user.id, data.items)
    return SyncBatchResponse(
        synced=result["synced"],
        conflicts=result["conflicts"],
        failed=result["failed"],
        server_version=result["server_version"]
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sync status for a device"""
    service = OfflineService(db)
    status = service.get_sync_status(current_user.id, device_id)
    if not status:
        raise HTTPException(status_code=404, detail="Device not found")
    return status


@router.post("/sync/delta", response_model=DeltaSyncResponse)
def get_delta_changes(
    data: DeltaSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get changes since a version (delta sync)"""
    service = OfflineService(db)
    items, version, has_more = service.get_delta_changes(
        tenant.id,
        current_user.id,
        data.since_version,
        data.entity_types
    )
    return DeltaSyncResponse(
        items=items,
        current_version=version,
        has_more=has_more
    )


# Conflict resolution
@router.get("/conflicts", response_model=List[SyncConflictResponse])
def get_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unresolved sync conflicts"""
    service = OfflineService(db)
    return service.get_user_conflicts(current_user.id)


@router.post("/conflicts/{conflict_id}/resolve", response_model=SyncConflictResponse)
def resolve_conflict(
    conflict_id: str,
    data: ConflictResolution,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve a sync conflict"""
    service = OfflineService(db)
    conflict = service.resolve_conflict(conflict_id, current_user.id, data)
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return conflict


# Offline documents
@router.post("/documents", response_model=OfflineDocumentResponse)
def mark_document_offline(
    data: OfflineDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Mark a document for offline availability"""
    service = OfflineService(db)
    return service.mark_for_offline(tenant.id, current_user.id, data)


@router.get("/documents", response_model=List[OfflineDocumentResponse])
def get_offline_documents(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get documents marked for offline on a device"""
    service = OfflineService(db)
    return service.get_offline_documents(current_user.id, device_id)


@router.delete("/documents/{document_id}")
def remove_offline_document(
    document_id: str,
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a document from offline availability"""
    service = OfflineService(db)
    if not service.remove_from_offline(current_user.id, document_id, device_id):
        raise HTTPException(status_code=404, detail="Offline document not found")
    return {"message": "Document removed from offline"}


@router.put("/documents/{offline_doc_id}/synced", response_model=OfflineDocumentResponse)
def mark_document_synced(
    offline_doc_id: str,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an offline document as synced"""
    service = OfflineService(db)
    doc = service.mark_synced(offline_doc_id, version)
    if not doc:
        raise HTTPException(status_code=404, detail="Offline document not found")
    return doc


# Storage tracking
@router.put("/devices/{device_id}/storage")
def update_storage(
    device_id: str,
    bytes_used: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update storage used on a device"""
    service = OfflineService(db)
    device = service.update_storage_used(device_id, bytes_used)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"storage_used_mb": device.storage_used, "storage_quota_mb": device.storage_quota}
