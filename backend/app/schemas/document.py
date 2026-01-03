from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.document import SourceType, Classification, LifecycleStatus, OCRStatus, ApprovalFlowType, FieldType


# Document Type schemas
class DocumentTypeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    retention_days: Optional[int] = None
    approval_flow_type: ApprovalFlowType = ApprovalFlowType.NONE
    auto_approvers: Optional[List[str]] = None


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    retention_days: Optional[int] = None
    approval_flow_type: Optional[ApprovalFlowType] = None
    auto_approvers: Optional[List[str]] = None


class DocumentTypeResponse(DocumentTypeBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Folder schemas
class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[str] = None


class FolderCreate(FolderBase):
    pass


class FolderResponse(FolderBase):
    id: str
    path: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Department schemas
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(DepartmentBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Custom Field schemas
class CustomFieldBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    field_key: str = Field(..., min_length=2, max_length=100, pattern="^[a-z_][a-z0-9_]*$")
    field_type: FieldType
    options: Optional[List[str]] = None
    required: bool = False
    default_value: Optional[str] = None
    document_type_id: Optional[str] = None


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldResponse(CustomFieldBase):
    id: str
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Document schemas
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    source_type: SourceType
    document_type_id: str
    customer_id: Optional[str] = None
    vendor_id: Optional[str] = None
    department_id: Optional[str] = None
    folder_id: Optional[str] = None
    classification: Classification = Classification.INTERNAL
    custom_metadata: Dict[str, Any] = {}


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    folder_id: Optional[str] = None
    classification: Optional[Classification] = None
    custom_metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    id: str
    title: str
    file_name: str
    file_size: int
    mime_type: str
    page_count: Optional[int]
    source_type: SourceType
    customer_id: Optional[str]
    vendor_id: Optional[str]
    department_id: Optional[str]
    document_type_id: str
    folder_id: Optional[str]
    classification: Classification
    lifecycle_status: LifecycleStatus
    is_worm_locked: bool
    legal_hold: bool
    ocr_status: OCRStatus
    custom_metadata: Dict[str, Any]
    tenant_id: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    # Nested objects
    document_type: Optional[DocumentTypeResponse] = None
    folder: Optional[FolderResponse] = None
    department: Optional[DepartmentResponse] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# Version schemas
class VersionResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    file_size: int
    checksum_sha256: str
    change_reason: Optional[str]
    is_current: bool
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class VersionCreate(BaseModel):
    change_reason: Optional[str] = None


# Lifecycle transition
class LifecycleTransitionRequest(BaseModel):
    to_status: LifecycleStatus
    reason: Optional[str] = None
