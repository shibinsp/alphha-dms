"""Entity Management API - Customers, Vendors, Departments, Document Types."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, require_permissions
from app.models import (
    User, Document, Department, DocumentType, CustomField,
    SourceType, FieldType, ApprovalFlowType
)
from app.models.entities import Customer, Vendor
from app.schemas.entities import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    VendorCreate, VendorUpdate, VendorResponse,
    DepartmentCreate, DepartmentResponse,
    DocumentTypeCreate, DocumentTypeUpdate, DocumentTypeResponse,
    CustomFieldCreate, CustomFieldResponse
)

router = APIRouter()


# ============ CUSTOMERS ============
@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all customers with document counts."""
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)
    
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.external_id.ilike(f"%{search}%"))
        )
    
    customers = query.offset(skip).limit(limit).all()
    
    # Add document counts
    result = []
    for c in customers:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.customer_id == c.external_id,
            Document.tenant_id == current_user.tenant_id
        ).scalar()
        resp = CustomerResponse.model_validate(c)
        resp.document_count = doc_count
        result.append(resp)
    
    return result


@router.post("/customers", response_model=CustomerResponse)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Create or update customer from CRM sync."""
    existing = db.query(Customer).filter(
        Customer.external_id == data.external_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if existing:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        db.commit()
        return existing
    
    customer = Customer(**data.model_dump(), tenant_id=current_user.tenant_id)
    db.add(customer)
    db.commit()
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer details with documents."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    doc_count = db.query(func.count(Document.id)).filter(
        Document.customer_id == customer.external_id
    ).scalar()
    
    resp = CustomerResponse.model_validate(customer)
    resp.document_count = doc_count
    return resp


@router.get("/customers/{customer_id}/documents")
def get_customer_documents(
    customer_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a customer."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    docs = db.query(Document).filter(
        Document.customer_id == customer.external_id,
        Document.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    
    return docs


# ============ VENDORS ============
@router.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all vendors with document counts."""
    query = db.query(Vendor).filter(Vendor.tenant_id == current_user.tenant_id)
    
    if search:
        query = query.filter(
            (Vendor.name.ilike(f"%{search}%")) |
            (Vendor.external_id.ilike(f"%{search}%"))
        )
    
    vendors = query.offset(skip).limit(limit).all()
    
    result = []
    for v in vendors:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.vendor_id == v.external_id,
            Document.tenant_id == current_user.tenant_id
        ).scalar()
        resp = VendorResponse.model_validate(v)
        resp.document_count = doc_count
        result.append(resp)
    
    return result


@router.post("/vendors", response_model=VendorResponse)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Create or update vendor from ERP sync."""
    existing = db.query(Vendor).filter(
        Vendor.external_id == data.external_id,
        Vendor.tenant_id == current_user.tenant_id
    ).first()
    
    if existing:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        db.commit()
        return existing
    
    vendor = Vendor(**data.model_dump(), tenant_id=current_user.tenant_id)
    db.add(vendor)
    db.commit()
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get vendor details."""
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.tenant_id == current_user.tenant_id
    ).first()
    
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    
    doc_count = db.query(func.count(Document.id)).filter(
        Document.vendor_id == vendor.external_id
    ).scalar()
    
    resp = VendorResponse.model_validate(vendor)
    resp.document_count = doc_count
    return resp


@router.get("/vendors/{vendor_id}/documents")
def get_vendor_documents(
    vendor_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a vendor."""
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.tenant_id == current_user.tenant_id
    ).first()
    
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    
    docs = db.query(Document).filter(
        Document.vendor_id == vendor.external_id,
        Document.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    
    return docs


# ============ DEPARTMENTS ============
@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all departments."""
    depts = db.query(Department).filter(
        Department.tenant_id == current_user.tenant_id
    ).all()
    
    result = []
    for d in depts:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.department_id == d.id
        ).scalar()
        resp = DepartmentResponse.model_validate(d)
        resp.document_count = doc_count
        result.append(resp)
    
    return result


@router.post("/departments", response_model=DepartmentResponse)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Create a department."""
    dept = Department(**data.model_dump(), tenant_id=current_user.tenant_id)
    db.add(dept)
    db.commit()
    return dept


@router.get("/departments/{dept_id}/documents")
def get_department_documents(
    dept_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a department."""
    docs = db.query(Document).filter(
        Document.department_id == dept_id,
        Document.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    
    return docs


# ============ DOCUMENT TYPES ============
@router.get("/document-types", response_model=List[DocumentTypeResponse])
def list_document_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all document types with custom fields."""
    types = db.query(DocumentType).filter(
        DocumentType.tenant_id == current_user.tenant_id
    ).all()
    return types


@router.post("/document-types", response_model=DocumentTypeResponse)
def create_document_type(
    data: DocumentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Create a document type."""
    doc_type = DocumentType(
        name=data.name,
        description=data.description,
        icon=data.icon,
        retention_days=data.retention_days,
        approval_flow_type=ApprovalFlowType(data.approval_flow_type),
        auto_approvers=data.auto_approvers,
        tenant_id=current_user.tenant_id
    )
    db.add(doc_type)
    db.commit()
    return doc_type


@router.put("/document-types/{type_id}", response_model=DocumentTypeResponse)
def update_document_type(
    type_id: str,
    data: DocumentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Update a document type."""
    doc_type = db.query(DocumentType).filter(
        DocumentType.id == type_id,
        DocumentType.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc_type:
        raise HTTPException(404, "Document type not found")
    
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "approval_flow_type" and v:
            v = ApprovalFlowType(v)
        setattr(doc_type, k, v)
    
    db.commit()
    return doc_type


# ============ CUSTOM FIELDS ============
@router.get("/custom-fields", response_model=List[CustomFieldResponse])
def list_custom_fields(
    document_type_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List custom fields, optionally filtered by document type."""
    query = db.query(CustomField).filter(
        CustomField.tenant_id == current_user.tenant_id
    )
    
    if document_type_id:
        query = query.filter(
            (CustomField.document_type_id == document_type_id) |
            (CustomField.document_type_id.is_(None))  # Global fields
        )
    
    return query.all()


@router.post("/custom-fields", response_model=CustomFieldResponse)
def create_custom_field(
    data: CustomFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Create a custom metadata field."""
    field = CustomField(
        name=data.name,
        field_key=data.field_key,
        field_type=FieldType(data.field_type),
        options=data.options,
        required=data.required,
        default_value=data.default_value,
        document_type_id=data.document_type_id,
        tenant_id=current_user.tenant_id
    )
    db.add(field)
    db.commit()
    return field


@router.delete("/custom-fields/{field_id}")
def delete_custom_field(
    field_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("admin"))
):
    """Delete a custom field."""
    field = db.query(CustomField).filter(
        CustomField.id == field_id,
        CustomField.tenant_id == current_user.tenant_id
    ).first()
    
    if not field:
        raise HTTPException(404, "Custom field not found")
    
    db.delete(field)
    db.commit()
    return {"status": "deleted"}
