import os
import hashlib
import uuid
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.api.v1.dependencies import (
    get_current_user, get_current_tenant,
    require_permissions, require_any_permission
)
from app.services.audit_service import AuditService
from app.services.mistral_ocr_service import MistralOCRService
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
    SourceType, LifecycleStatus, OCRStatus, Classification
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
    current_user: User = Depends(require_permissions("documents:create")),
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
    show_pending: Optional[bool] = Query(False, description="Show pending approval documents (for reviewers)"),
    current_user: User = Depends(require_permissions("documents:read")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List documents with filters and pagination.
    Documents in DRAFT/REVIEW status are only visible to:
    - The document owner (creator)
    - Admins and Managers (reviewers)
    Regular users only see APPROVED/ARCHIVED documents in the main list.
    """
    from sqlalchemy import or_, and_
    
    # Get user roles
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin = any(r in ['admin', 'super_admin'] for r in user_roles)
    is_manager = 'manager' in user_roles
    is_reviewer = any(r in ['manager', 'admin', 'super_admin'] for r in user_roles)
    
    query = db.query(Document).filter(
        Document.tenant_id == tenant.id,
        Document.lifecycle_status != LifecycleStatus.DELETED
    )

    # Filter by approval status - key logic for showing only approved documents
    if lifecycle_status:
        # If specific status requested, apply it
        query = query.filter(Document.lifecycle_status == lifecycle_status)
    else:
        # Default behavior: filter based on user role
        if is_admin or is_manager:
            # Admins/Managers see all documents (approved + pending)
            pass
        else:
            # Regular users: only see APPROVED/ARCHIVED documents OR their own documents
            query = query.filter(
                or_(
                    Document.lifecycle_status.in_([LifecycleStatus.APPROVED, LifecycleStatus.ARCHIVED]),
                    Document.created_by == current_user.id  # Always see own documents
                )
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    source_type: SourceType = Form(...),
    document_type_id: str = Form(...),
    customer_id: Optional[str] = Form(None),
    vendor_id: Optional[str] = Form(None),
    department_id: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    classification: str = Form("INTERNAL"),
    current_user: User = Depends(require_permissions("documents:create")),
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

    # Virus scan
    from app.services.virus_scanner import scan_file_content
    is_clean, scan_result = scan_file_content(content)
    if not is_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected: malware detected ({scan_result})"
        )

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

    # Trigger OCR automatically
    document.ocr_status = OCRStatus.PROCESSING
    db.commit()
    background_tasks.add_task(
        process_ocr,
        document.id,
        document.file_path,
        document.file_name,
        document.mime_type
    )

    return document


def process_ocr(document_id: str, file_path: str, file_name: str, mime_type: str):
    """Background task to process OCR."""
    import asyncio
    from app.core.database import SessionLocal
    
    print(f"Starting OCR for document {document_id}")
    
    async def run_ocr():
        db = SessionLocal()
        try:
            print(f"Reading file: {file_path}")
            with open(file_path, 'rb') as f:
                content = f.read()
            
            print(f"Calling Mistral OCR service...")
            result = await MistralOCRService.extract_text_and_metadata(content, file_name, mime_type)
            print(f"OCR result: success={result.get('success')}, text_len={len(result.get('text', ''))}")
            
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and result.get('success'):
                doc.ocr_text = result.get('text', '')
                doc.extracted_metadata = {
                    'document_type': result.get('document_type'),
                    'language': result.get('language'),
                    'confidence': result.get('confidence'),
                    'entities': result.get('entities', {}),
                    'metadata': result.get('metadata', {})
                }
                doc.ocr_status = OCRStatus.COMPLETED
                db.commit()
                print(f"OCR completed for document {document_id}")
            elif doc:
                doc.ocr_status = OCRStatus.FAILED
                doc.extracted_metadata = {'error': result.get('error', 'Unknown error')}
                db.commit()
                print(f"OCR failed for document {document_id}: {result.get('error')}")
        except Exception as e:
            print(f"OCR Error for {document_id}: {e}")
            import traceback
            traceback.print_exc()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.ocr_status = OCRStatus.FAILED
                doc.extracted_metadata = {'error': str(e)}
                db.commit()
        finally:
            db.close()
    
    asyncio.run(run_ocr())


@router.get("/{document_id}")
async def get_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(require_permissions("documents:read")),
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

    # Check classification-based access
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin = any(r in ['admin', 'super_admin'] for r in user_roles)
    is_manager = 'manager' in user_roles
    is_reviewer = any(r in ['manager', 'admin', 'super_admin', 'legal', 'compliance'] for r in user_roles)
    is_owner = document.created_by == current_user.id
    
    # Check access for RESTRICTED documents
    from app.models import AccessRequest, AccessRequestStatus
    has_approved_access = False
    has_pending_request = False
    
    if document.classification == Classification.RESTRICTED and not is_owner:
        approved_request = db.query(AccessRequest).filter(
            AccessRequest.document_id == document.id,
            AccessRequest.requester_id == current_user.id,
            AccessRequest.status == AccessRequestStatus.APPROVED
        ).first()
        has_approved_access = approved_request is not None
        
        if not has_approved_access:
            pending_request = db.query(AccessRequest).filter(
                AccessRequest.document_id == document.id,
                AccessRequest.requester_id == current_user.id,
                AccessRequest.status.in_([AccessRequestStatus.PENDING, AccessRequestStatus.REASON_REQUESTED])
            ).first()
            has_pending_request = pending_request is not None
    
    # Determine access level
    if document.classification == Classification.RESTRICTED:
        # RESTRICTED: only owner or users with approved access request
        can_access = is_owner or has_approved_access
    elif document.classification == Classification.CONFIDENTIAL:
        can_access = is_owner or is_manager or is_admin
    elif document.classification == Classification.INTERNAL:
        can_access = is_owner or is_reviewer
    else:  # PUBLIC
        can_access = True
    
    # For RESTRICTED documents without access, return limited info with access_required flag
    if document.classification == Classification.RESTRICTED and not can_access:
        return {
            "id": document.id,
            "title": document.title,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "classification": document.classification,
            "lifecycle_status": document.lifecycle_status,
            "source_type": document.source_type,
            "document_type_id": document.document_type_id,
            "created_at": document.created_at,
            "created_by": document.created_by,
            "tenant_id": document.tenant_id,
            "access_required": True,
            "has_pending_request": has_pending_request,
            "owner_id": document.created_by
        }
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this document."
        )

    # Log view event
    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="documents:readed",
        entity_type="document",
        entity_id=document.id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )

    # Get user's permission level for this document
    user_permission = None
    if not is_owner and not is_admin:
        from app.models import DocumentPermission
        perm = db.query(DocumentPermission).filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.revoked == False
        ).first()
        if perm:
            user_permission = perm.permission_level.value if perm.permission_level else None

    # Return full document data
    return {
        "id": document.id,
        "title": document.title,
        "file_name": document.file_name,
        "file_path": document.file_path,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "page_count": document.page_count,
        "checksum_sha256": document.checksum_sha256,
        "source_type": document.source_type,
        "customer_id": document.customer_id,
        "vendor_id": document.vendor_id,
        "department_id": document.department_id,
        "document_type_id": document.document_type_id,
        "folder_id": document.folder_id,
        "classification": document.classification,
        "lifecycle_status": document.lifecycle_status,
        "is_worm_locked": document.is_worm_locked,
        "retention_expiry": document.retention_expiry,
        "legal_hold": document.legal_hold,
        "legal_hold_by": document.legal_hold_by,
        "legal_hold_at": document.legal_hold_at,
        "current_version_id": document.current_version_id,
        "ocr_text": document.ocr_text,
        "ocr_status": document.ocr_status,
        "ocr_confidence": document.ocr_confidence,
        "extracted_metadata": document.extracted_metadata,
        "custom_metadata": document.custom_metadata,
        "tenant_id": document.tenant_id,
        "created_by": document.created_by,
        "updated_by": document.updated_by,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "user_permission": user_permission,
        "is_owner": is_owner,
    }


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    request: Request,
    document_id: str,
    document_data: DocumentUpdate,
    current_user: User = Depends(require_permissions("documents:update")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Update document metadata. Automatically creates a new version.
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

    # Block updates while document is in REVIEW
    if document.lifecycle_status == LifecycleStatus.REVIEW:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document is pending review and cannot be modified"
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

    # Store old values for audit
    old_values = {
        "title": document.title,
        "classification": document.classification.value if document.classification else None,
        "folder_id": document.folder_id,
        "custom_metadata": document.custom_metadata
    }

    # Get update data
    update_data = document_data.model_dump(exclude_unset=True)
    
    # Check if any actual changes
    has_changes = any(
        getattr(document, field, None) != value 
        for field, value in update_data.items()
    )
    
    if has_changes:
        # Create new version with metadata snapshot
        max_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        new_version_number = (max_version.version_number + 1) if max_version else 1
        
        # Mark previous versions as not current
        db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).update({"is_current": False})
        
        # Create new version (same file, new metadata)
        new_version = DocumentVersion(
            id=str(uuid.uuid4()),
            document_id=document_id,
            version_number=new_version_number,
            file_path=document.file_path,
            file_size=document.file_size,
            checksum_sha256=document.checksum_sha256,
            metadata_snapshot=old_values,
            change_reason="Metadata updated",
            is_current=True,
            created_by=current_user.id
        )
        db.add(new_version)
        document.current_version_id = new_version.id

    # Update fields
    for field, value in update_data.items():
        setattr(document, field, value)

    document.updated_by = current_user.id
    document.updated_at = datetime.utcnow()
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
    current_user: User = Depends(require_permissions("documents:delete")),
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
        event_type="documents:deleted",
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
    current_user: User = Depends(require_permissions("documents:read")),
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

    # Check if user has download permission
    is_owner = document.created_by == current_user.id
    user_roles = [r.name for r in current_user.roles] if current_user.roles else []
    is_admin = any(r in ['admin', 'super_admin'] for r in user_roles)
    
    if not is_owner and not is_admin:
        # Check document permission level
        from app.models import DocumentPermission, PermissionLevel
        permission = db.query(DocumentPermission).filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.revoked == False
        ).first()
        
        if permission and permission.permission_level == PermissionLevel.VIEWER_NO_DOWNLOAD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to download this document"
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
        event_type="documents:readed",
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


@router.post("/{document_id}/ocr")
async def trigger_ocr(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Trigger OCR processing for a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Update status to processing
    document.ocr_status = OCRStatus.PROCESSING
    db.commit()

    # Run OCR in background
    background_tasks.add_task(
        process_ocr,
        document.id,
        document.file_path,
        document.file_name,
        document.mime_type
    )

    return {"message": "OCR processing started", "status": "processing"}


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
    current_user: User = Depends(require_permissions("documents:read")),
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


@router.get("/{document_id}/versions/{version_number}/download")
async def download_version(
    document_id: str,
    version_number: int,
    current_user: User = Depends(require_permissions("documents:read")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Download a specific version of a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == version_number
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if not os.path.exists(version.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    filename = f"v{version_number}_{document.file_name}"
    return FileResponse(
        version.file_path,
        media_type=document.mime_type,
        filename=sanitize_filename(filename)
    )


@router.post("/{document_id}/versions", response_model=VersionResponse)
async def upload_new_version(
    request: Request,
    document_id: str,
    file: UploadFile = File(...),
    change_summary: str = Form(...),
    current_user: User = Depends(require_permissions("documents:update")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Upload a new version of a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.is_worm_locked:
        raise HTTPException(status_code=403, detail="Document is WORM locked")

    # Block new versions while document is in REVIEW (pending approval)
    if document.lifecycle_status == LifecycleStatus.REVIEW:
        raise HTTPException(
            status_code=403, 
            detail="Document is pending review. New versions cannot be created until the review is completed or rejected."
        )

    # Block new versions for APPROVED documents (must be unlocked first)
    if document.lifecycle_status == LifecycleStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail="Document is approved and locked. Cannot create new versions."
        )

    # Get current max version
    max_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    new_version_number = (max_version.version_number + 1) if max_version else 1

    # Save file
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    unique_prefix = uuid.uuid4().hex[:16]
    safe_filename = sanitize_filename(file.filename or "document")
    relative_path = f"./uploads/{tenant.id}/{date_path}/{unique_prefix}_{safe_filename}"
    
    os.makedirs(os.path.dirname(relative_path), exist_ok=True)
    with open(relative_path, "wb") as f:
        f.write(file_content)

    # Create new version
    version = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=document_id,
        version_number=new_version_number,
        file_path=relative_path,
        file_size=len(file_content),
        checksum_sha256=file_hash,
        change_reason=change_summary,
        is_current=True,
        created_by=current_user.id
    )
    
    # Mark previous versions as not current
    db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).update({"is_current": False})
    
    db.add(version)

    # Update document with new file info
    document.file_path = relative_path
    document.file_size = len(file_content)
    document.file_name = safe_filename
    document.checksum_sha256 = file_hash
    document.current_version_id = version.id
    document.updated_by = current_user.id
    document.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(version)

    # Log audit event
    audit_service = AuditService(db)
    audit_service.log_event(
        event_type="documents:version_created",
        entity_type="document",
        entity_id=document_id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        new_values={"version": new_version_number, "change_summary": change_summary}
    )

    return version


# Lifecycle transition
@router.post("/{document_id}/transition", response_model=DocumentResponse)
async def transition_lifecycle(
    request: Request,
    document_id: str,
    transition: LifecycleTransitionRequest,
    current_user: User = Depends(require_any_permission("document.approve", "documents:update")),
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

    # If transitioning to REVIEW, create an approval request
    if transition.to_status == LifecycleStatus.REVIEW:
        from app.services.workflow_service import WorkflowService
        from app.schemas.workflow import SubmitApprovalRequest
        
        workflow_service = WorkflowService(db)
        submit_data = SubmitApprovalRequest(priority="NORMAL")
        try:
            workflow_service.submit_for_approval(document_id, tenant.id, current_user.id, submit_data)
            db.refresh(document)
            return document
        except HTTPException as e:
            if "already has a pending" in str(e.detail):
                # Already has pending request, just update status
                pass
            else:
                raise e

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
