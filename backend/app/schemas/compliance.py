"""Compliance Schemas - M06 WORM, M07 Retention, M08 Legal Hold"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.models.compliance import RetentionUnit, RetentionAction, LegalHoldStatus


# WORM Record Schemas
class WORMRecordBase(BaseModel):
    retention_until: datetime
    lock_reason: Optional[str] = None


class WORMLockRequest(WORMRecordBase):
    pass


class WORMRecordResponse(WORMRecordBase):
    id: str
    document_id: str
    tenant_id: str
    locked_at: datetime
    locked_by: str
    retention_extended: bool
    original_retention_until: Optional[datetime] = None
    content_hash: str
    last_verified_at: Optional[datetime] = None
    verification_count: int

    class Config:
        from_attributes = True


class WORMExtendRequest(BaseModel):
    new_retention_until: datetime
    reason: Optional[str] = None


class WORMVerifyResponse(BaseModel):
    document_id: str
    is_valid: bool
    original_hash: str
    current_hash: str
    verified_at: datetime
    message: str


# Retention Policy Schemas
class RetentionPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    document_type_id: Optional[str] = None
    source_type: Optional[str] = None
    classification: Optional[str] = None
    retention_period: int
    retention_unit: RetentionUnit
    expiry_action: RetentionAction
    notify_days_before: int = 30
    notify_roles: Optional[List[str]] = None
    auto_apply: bool = True
    priority: int = 0
    is_active: bool = True


class RetentionPolicyCreate(RetentionPolicyBase):
    pass


class RetentionPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    document_type_id: Optional[str] = None
    source_type: Optional[str] = None
    classification: Optional[str] = None
    retention_period: Optional[int] = None
    retention_unit: Optional[RetentionUnit] = None
    expiry_action: Optional[RetentionAction] = None
    notify_days_before: Optional[int] = None
    notify_roles: Optional[List[str]] = None
    auto_apply: Optional[bool] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class RetentionPolicyResponse(RetentionPolicyBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class PolicyExecutionLogResponse(BaseModel):
    id: str
    tenant_id: str
    policy_id: str
    document_id: str
    action_taken: RetentionAction
    action_status: str
    action_result: Optional[str] = None
    executed_at: datetime
    executed_by: str

    class Config:
        from_attributes = True


# Legal Hold Schemas
class LegalHoldBase(BaseModel):
    hold_name: str
    case_number: Optional[str] = None
    matter_name: Optional[str] = None
    description: Optional[str] = None
    legal_counsel: Optional[str] = None
    counsel_email: Optional[str] = None
    hold_end_date: Optional[datetime] = None
    scope_criteria: Optional[Dict[str, Any]] = None


class LegalHoldCreate(LegalHoldBase):
    document_ids: Optional[List[str]] = None


class LegalHoldUpdate(BaseModel):
    hold_name: Optional[str] = None
    case_number: Optional[str] = None
    matter_name: Optional[str] = None
    description: Optional[str] = None
    legal_counsel: Optional[str] = None
    counsel_email: Optional[str] = None
    hold_end_date: Optional[datetime] = None


class LegalHoldResponse(LegalHoldBase):
    id: str
    tenant_id: str
    hold_start_date: datetime
    status: LegalHoldStatus
    documents_held: int
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None
    release_reason: Optional[str] = None

    class Config:
        from_attributes = True


class LegalHoldDocumentResponse(BaseModel):
    id: str
    legal_hold_id: str
    document_id: str
    added_at: datetime
    added_by: str
    snapshot_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class LegalHoldReleaseRequest(BaseModel):
    reason: str


class AddDocumentsToHoldRequest(BaseModel):
    document_ids: List[str]


# Evidence Export Schemas
class EvidenceExportCreate(BaseModel):
    export_name: str
    export_format: str = "ZIP"
    document_ids: Optional[List[str]] = None  # If None, export all in hold


class EvidenceExportResponse(BaseModel):
    id: str
    tenant_id: str
    legal_hold_id: str
    export_name: str
    export_format: str
    export_path: Optional[str] = None
    manifest: Optional[Dict[str, Any]] = None
    document_count: int
    total_size_bytes: int
    exported_at: datetime
    exported_by: str
    export_hash: Optional[str] = None
    delivered_to: Optional[str] = None
    delivered_at: Optional[datetime] = None
    delivery_method: Optional[str] = None

    class Config:
        from_attributes = True


# Expiring Documents Response
class ExpiringDocumentResponse(BaseModel):
    document_id: str
    document_title: str
    policy_name: str
    expiry_date: datetime
    days_until_expiry: int
    action_on_expiry: RetentionAction
