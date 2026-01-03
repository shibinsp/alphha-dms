"""Offline/Sync schemas for M17"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.offline import SyncStatus, SyncOperation


class DeviceRegistrationCreate(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    browser_info: Optional[str] = None


class DeviceRegistrationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    device_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    os_info: Optional[str]
    browser_info: Optional[str]
    last_sync_at: Optional[datetime]
    sync_version: int
    storage_quota: int
    storage_used: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncQueueItemCreate(BaseModel):
    device_id: str
    entity_type: str
    entity_id: Optional[str] = None
    local_id: str
    operation: SyncOperation
    payload: Dict[str, Any] = Field(default_factory=dict)
    client_timestamp: datetime


class SyncQueueItemResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    device_id: str
    entity_type: str
    entity_id: Optional[str]
    local_id: str
    operation: SyncOperation
    payload: Dict[str, Any]
    status: SyncStatus
    attempts: int
    last_attempt_at: Optional[datetime]
    error_message: Optional[str]
    client_timestamp: datetime
    created_at: datetime
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncBatchRequest(BaseModel):
    device_id: str
    items: List[SyncQueueItemCreate]


class SyncBatchResponse(BaseModel):
    synced: List[SyncQueueItemResponse]
    conflicts: List["SyncConflictResponse"]
    failed: List[SyncQueueItemResponse]
    server_version: int


class SyncConflictResponse(BaseModel):
    id: str
    sync_queue_id: str
    entity_type: str
    entity_id: str
    client_data: Dict[str, Any]
    server_data: Dict[str, Any]
    client_timestamp: datetime
    server_timestamp: datetime
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ConflictResolution(BaseModel):
    resolution: str  # client_wins, server_wins, merged
    merged_data: Optional[Dict[str, Any]] = None


class OfflineDocumentCreate(BaseModel):
    document_id: str
    device_id: str


class OfflineDocumentResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    document_id: str
    device_id: str
    is_synced: bool
    synced_version: Optional[int]
    synced_at: Optional[datetime]
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    device_id: str
    last_sync_at: Optional[datetime]
    server_version: int
    pending_changes: int
    conflicts_count: int
    storage_used: int
    storage_quota: int


class DeltaSyncRequest(BaseModel):
    device_id: str
    since_version: int
    entity_types: List[str] = Field(default_factory=list)


class DeltaSyncItem(BaseModel):
    entity_type: str
    entity_id: str
    operation: str  # create, update, delete
    data: Optional[Dict[str, Any]]
    version: int
    timestamp: datetime


class DeltaSyncResponse(BaseModel):
    items: List[DeltaSyncItem]
    current_version: int
    has_more: bool


# Update forward reference
SyncBatchResponse.model_rebuild()
