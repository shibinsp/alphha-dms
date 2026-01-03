import os
import hashlib
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.api.v1.dependencies import (
    get_current_user, get_current_tenant,
    require_permissions, require_any_permission
)
from app.services.audit_service import AuditService
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    DocumentTypeCreate, DocumentTypeResponse,
    FolderCreate, FolderResponse,
    DepartmentCreate, DepartmentResponse,
    VersionResponse, VersionCreate,
    LifecycleTransitionRequest
)
from app.models.document import (
    Document, DocumentType, Folder, Department,
    SourceType, LifecycleStatus, OCRStatus
)
from app.models.version import DocumentVersion, DocumentLock
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()
settings = get_settings()


def sanitize_filename(filename: str) -> str:
    """Remove path traversal sequences and get safe filename."""
    # Get basename to remove any path components
    safe_name = os.path.basename(filename)
    # Remove any remaining path traversal attempts
    safe_name = safe_name.replace('..', '').replace('/', '').replace('\\', '')
    # Ensure we have a valid filename
    if not safe_name or safe_name.startswith('.'):
        safe_name = f"file_{uuid.uuid4().hex[:8]}"
    return safe_name.strip()


def validate_file_path(file_path: str) -> bool:
    """Ensure file path is within upload directory."""
    try:
        upload_dir = os.path.realpath(settings.UPLOAD_DIR)
        real_path = os.path.realpath(file_path)
        return real_path.startswith(upload_dir + os.sep) or real_path == upload_dir
    except Exception:
        return False


def get_file_path(tenant_id: str, filename: str) -> str:
    """Generate storage path for uploaded file with sanitized filename."""
    safe_filename = sanitize_filename(filename)
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
    return os.path.join(settings.UPLOAD_DIR, tenant_id, date_path, unique_name)


# ============ Non-parameterized routes FIRST to avoid matching as document_id ============

# Document Type endpoints
@router.get("/types", response_model=List[DocumentTypeResponse])
async def list_document_types(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List document types.
    """
    types = db.query(DocumentType).filter(
        DocumentType.tenant_id == tenant.id
    ).all()
    return types


@router.post("/types", response_model=DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_document_type(
    type_data: DocumentTypeCreate,
    current_user: User = Depends(require_permissions("admin.policies")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create document type.
    """
    doc_type = DocumentType(
        name=type_data.name,
        description=type_data.description,
        icon=type_data.icon,
        retention_days=type_data.retention_days,
        approval_flow_type=type_data.approval_flow_type,
        auto_approvers=type_data.auto_approvers,
        tenant_id=tenant.id
    )

    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)

    return doc_type


# Folder endpoints
@router.get("/folders", response_model=List[FolderResponse])
async def list_folders(
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List folders.
    """
    query = db.query(Folder).filter(Folder.tenant_id == tenant.id)
    if parent_id:
        query = query.filter(Folder.parent_id == parent_id)
    else:
        query = query.filter(Folder.parent_id.is_(None))

    return query.all()


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(require_permissions("document.upload")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create folder.
    """
    # Build path
    if folder_data.parent_id:
        parent = db.query(Folder).filter(
            Folder.id == folder_data.parent_id,
            Folder.tenant_id == tenant.id
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent folder not found"
            )
        path = f"{parent.path}/{folder_data.name}"
    else:
        path = f"/{folder_data.name}"

    folder = Folder(
        name=folder_data.name,
        parent_id=folder_data.parent_id,
        path=path,
        tenant_id=tenant.id
    )

    db.add(folder)
    db.commit()
    db.refresh(folder)

    return folder


# Department endpoints
@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List departments.
    """
    return db.query(Department).filter(Department.tenant_id == tenant.id).all()


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept_data: DepartmentCreate,
    current_user: User = Depends(require_permissions("admin.policies")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create department.
    """
    dept = Department(
        name=dept_data.name,
        code=dept_data.code,
        tenant_id=tenant.id
    )

    db.add(dept)
    db.commit()
    db.refresh(dept)

    return dept


# ============ Document CRUD endpoints (parameterized routes AFTER static ones) ============

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source_type: Optional[SourceType] = None,
    document_type_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    lifecycle_status: Optional[LifecycleStatus] = None,
    customer_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    current_user: User = Depends(require_permissions("document.view")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List documents with filters and pagination.
    """
    query = db.query(Document).filter(
        Document.tenant_id == tenant.id,
        Document.lifecycle_status != LifecycleStatus.DELETED
    )

    if search:
        query = query.filter(
            (Document.title.ilike(f"%{search}%")) |
            (Document.file_name.ilike(f"%{search}%"))
        )

    if source_type:
        query = query.filter(Document.source_type == source_type)
    if document_type_id:
        query = query.filter(Document.document_type_id == document_type_id)
    if folder_id:
        query = query.filter(Document.folder_id == folder_id)
    if lifecycle_status:
        query = query.filter(Document.lifecycle_status == lifecycle_status)
    if customer_id:
        query = query.filter(Document.customer_id == customer_id)
    if vendor_id:
        query = query.filter(Document.vendor_id == vendor_id)

    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return DocumentListResponse(
        items=documents,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    source_type: SourceType = Form(...),
    document_type_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    vendor_id: Optional[str] = Form(None),
    department_id: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    classification: str = Form("INTERNAL"),
    current_user: User = Depends(require_permissions("document.upload")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Upload a new document.
    """
    audit_service = AuditService(db)

    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed"
        )

    # Validate document type exists
    doc_type = db.query(DocumentType).filter(
        DocumentType.id == document_type_id,
        DocumentType.tenant_id == tenant.id
    ).first()
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document type"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Compute checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Generate file path and save
    file_path = get_file_path(tenant.id, file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    document = Document(
        title=title,
        file_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        checksum_sha256=checksum,
        source_type=source_type,
        customer_id=customer_id,
        vendor_id=vendor_id,
        department_id=department_id,
        document_type_id=document_type_id,
        folder_id=folder_id,
        classification=classification,
        tenant_id=tenant.id,
        created_by=current_user.id,
        updated_by=current_user.id,
        ocr_status=OCRStatus.PENDING
    )

    db.add(document)
    db.flush()

    # Create initial version
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_path=file_path,
        file_size=len(content),
        checksum_sha256=checksum,
        metadata_snapshot={
            "title": title,
            "classification": classification
        },
        is_current=True,
        created_by=current_user.id
    )
    db.add(version)
    db.flush()

    document.current_version_id = version.id
    db.commit()
    db.refresh(document)

    # Log audit event
    audit_service.log_event(
        event_type="document.created",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        new_values={
            "title": document.title,
            "file_name": document.file_name,
            "source_type": document.source_type.value,
            "document_type": doc_type.name
        }
    )

    # TODO: Trigger OCR processing via Celery

    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(require_permissions("document.view")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get document details.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Log view event
    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="document.viewed",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    request: Request,
    document_id: str,
    document_data: DocumentUpdate,
    current_user: User = Depends(require_permissions("document.edit")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Update document metadata.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if document is locked
    if document.is_worm_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document is WORM locked and cannot be modified"
        )

    # Check for checkout lock
    lock = db.query(DocumentLock).filter(
        DocumentLock.document_id == document_id
    ).first()
    if lock and lock.locked_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document is checked out by another user"
        )

    # Store old values
    old_values = {
        "title": document.title,
        "classification": document.classification.value if document.classification else None,
        "folder_id": document.folder_id
    }

    # Update fields
    update_data = document_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    document.updated_by = current_user.id
    db.commit()
    db.refresh(document)

    # Log audit
    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="document.updated",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        old_values=old_values,
        new_values={
            "title": document.title,
            "classification": document.classification.value if document.classification else None,
            "folder_id": document.folder_id
        }
    )

    return document


@router.delete("/{document_id}")
async def delete_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(require_permissions("document.delete")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Soft delete document.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.is_worm_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete WORM locked document"
        )

    if document.legal_hold:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete document under legal hold"
        )

    document.lifecycle_status = LifecycleStatus.DELETED
    document.updated_by = current_user.id
    db.commit()

    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="document.deleted",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/download")
async def download_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(require_permissions("document.download")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Download document file.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Validate file path is within upload directory (prevent path traversal)
    if not validate_file_path(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage"
        )

    # Log download
    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="document.downloaded",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    try:
        return FileResponse(
            document.file_path,
            filename=sanitize_filename(document.file_name),
            media_type=document.mime_type
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error serving file"
        )


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Preview document file (inline display).
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not validate_file_path(document.file_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Return file for inline display
    return FileResponse(
        document.file_path,
        media_type=document.mime_type,
        headers={"Content-Disposition": f"inline; filename={sanitize_filename(document.file_name)}"}
    )


# Version endpoints
@router.get("/{document_id}/versions", response_model=List[VersionResponse])
async def list_versions(
    document_id: str,
    current_user: User = Depends(require_permissions("document.view")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List document versions.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).all()

    return versions


# Lifecycle transition
@router.post("/{document_id}/transition", response_model=DocumentResponse)
async def transition_lifecycle(
    request: Request,
    document_id: str,
    transition: LifecycleTransitionRequest,
    current_user: User = Depends(require_any_permission("document.approve", "document.edit")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Transition document lifecycle status.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Define allowed transitions
    allowed_transitions = {
        LifecycleStatus.DRAFT: [LifecycleStatus.REVIEW],
        LifecycleStatus.REVIEW: [LifecycleStatus.DRAFT, LifecycleStatus.APPROVED],
        LifecycleStatus.APPROVED: [LifecycleStatus.ARCHIVED],
        LifecycleStatus.ARCHIVED: [],
    }

    current_status = document.lifecycle_status
    if transition.to_status not in allowed_transitions.get(current_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status.value} to {transition.to_status.value}"
        )

    old_status = document.lifecycle_status.value
    document.lifecycle_status = transition.to_status
    document.updated_by = current_user.id
    db.commit()
    db.refresh(document)

    # Log transition
    audit_service = AuditService(db)
    event_type = {
        LifecycleStatus.REVIEW: "document.submitted_for_review",
        LifecycleStatus.APPROVED: "document.approved",
        LifecycleStatus.ARCHIVED: "document.archived",
        LifecycleStatus.DRAFT: "document.rejected"
    }.get(transition.to_status, "document.updated")

    audit_service.log_event(
        event_type=event_type,
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        old_values={"lifecycle_status": old_status},
        new_values={"lifecycle_status": document.lifecycle_status.value},
        metadata={"reason": transition.reason}
    )

    return document
