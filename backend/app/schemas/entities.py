"""Schemas for Customer, Vendor, and Entity management."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# Customer Schemas
class CustomerBase(BaseModel):
    external_id: str = Field(..., description="CRM Customer ID")
    name: str
    id_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerCreate(CustomerBase):
    crm_data: Optional[Dict[str, Any]] = {}


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    id_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    crm_data: Optional[Dict[str, Any]] = None


class CustomerResponse(CustomerBase):
    id: str
    crm_data: Dict[str, Any] = {}
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    document_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Vendor Schemas
class VendorBase(BaseModel):
    external_id: str = Field(..., description="ERP Vendor ID")
    name: str
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class VendorCreate(VendorBase):
    erp_data: Optional[Dict[str, Any]] = {}


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    erp_data: Optional[Dict[str, Any]] = None


class VendorResponse(VendorBase):
    id: str
    erp_data: Dict[str, Any] = {}
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    document_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Department Schemas
class DepartmentBase(BaseModel):
    name: str
    code: str


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(DepartmentBase):
    id: str
    created_at: datetime
    document_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Custom Field Schemas
class CustomFieldBase(BaseModel):
    name: str
    field_key: str
    field_type: str  # TEXT, NUMBER, DATE, SELECT, MULTI_SELECT, BOOLEAN
    options: Optional[List[str]] = None
    required: bool = False
    default_value: Optional[str] = None


class CustomFieldCreate(CustomFieldBase):
    document_type_id: Optional[str] = None


class CustomFieldResponse(CustomFieldBase):
    id: str
    document_type_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Document Type Schemas
class DocumentTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    retention_days: Optional[int] = None
    approval_flow_type: str = "NONE"  # AUTO, MANUAL, NONE


class DocumentTypeCreate(DocumentTypeBase):
    auto_approvers: Optional[List[str]] = None


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    retention_days: Optional[int] = None
    approval_flow_type: Optional[str] = None
    auto_approvers: Optional[List[str]] = None


class DocumentTypeResponse(DocumentTypeBase):
    id: str
    auto_approvers: Optional[List[str]] = None
    created_at: datetime
    custom_fields: List[CustomFieldResponse] = []

    class Config:
        from_attributes = True


# License Schemas
class LicenseValidate(BaseModel):
    license_key: str


class LicenseResponse(BaseModel):
    is_valid: bool
    expires_at: Optional[datetime] = None
    days_remaining: Optional[int] = None
    in_grace_period: bool = False
    message: str

    class Config:
        from_attributes = True
