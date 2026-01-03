"""PII Detection Schemas - M09"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.pii import PIIType, PIIAction


# PII Pattern Schemas
class PIIPatternBase(BaseModel):
    name: str
    pii_type: PIIType
    description: Optional[str] = None
    regex_pattern: str
    validator_function: Optional[str] = None
    mask_format: Optional[str] = None
    mask_char: str = "*"
    sensitivity_level: str = "HIGH"
    is_active: bool = True


class PIIPatternCreate(PIIPatternBase):
    pass


class PIIPatternUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    regex_pattern: Optional[str] = None
    validator_function: Optional[str] = None
    mask_format: Optional[str] = None
    mask_char: Optional[str] = None
    sensitivity_level: Optional[str] = None
    is_active: Optional[bool] = None


class PIIPatternResponse(PIIPatternBase):
    id: str
    tenant_id: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# PII Policy Schemas
class PIIPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    pii_types: List[PIIType]
    document_type_ids: Optional[List[str]] = None
    action: PIIAction
    exception_role_ids: Optional[List[str]] = None
    notify_on_detection: bool = True
    notify_roles: Optional[List[str]] = None
    priority: int = 0
    is_active: bool = True


class PIIPolicyCreate(PIIPolicyBase):
    pass


class PIIPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pii_types: Optional[List[PIIType]] = None
    document_type_ids: Optional[List[str]] = None
    action: Optional[PIIAction] = None
    exception_role_ids: Optional[List[str]] = None
    notify_on_detection: Optional[bool] = None
    notify_roles: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class PIIPolicyResponse(PIIPolicyBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Document PII Field Schemas
class DocumentPIIFieldResponse(BaseModel):
    id: str
    document_id: str
    pii_type: PIIType
    field_name: Optional[str] = None
    page_number: Optional[int] = None
    position_start: Optional[int] = None
    position_end: Optional[int] = None
    masked_value: Optional[str] = None
    confidence_score: Optional[str] = None
    action_taken: Optional[PIIAction] = None
    detected_at: datetime

    class Config:
        from_attributes = True


# PII Access Log Schemas
class PIIAccessLogResponse(BaseModel):
    id: str
    tenant_id: str
    pii_field_id: str
    document_id: str
    accessed_by: str
    access_type: str
    saw_unmasked: bool
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    accessed_at: datetime

    class Config:
        from_attributes = True


# Detection Request/Response
class PIIDetectionRequest(BaseModel):
    content: str
    detect_types: Optional[List[PIIType]] = None


class PIIDetectionResult(BaseModel):
    pii_type: PIIType
    original_value: str
    masked_value: str
    position_start: int
    position_end: int
    confidence_score: float


class PIIDetectionResponse(BaseModel):
    total_found: int
    results: List[PIIDetectionResult]
