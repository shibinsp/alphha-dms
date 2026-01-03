"""Document service for M02 - Document Management Core"""
import uuid
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import (
    Document, DocumentVersion, DocumentType, Folder, Department,
    DocumentLock, LifecycleStatus, OCRStatus, SourceType, Classification
)


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_path = os.getenv("UPLOAD_PATH", "/app/uploads")

    def create_document(
        self,
        tenant_id: str,
        user_id: str,
        title: str,
        file: BinaryIO,
        filename: str,
        document_type_id: str = None,
        department_id: str = None,
        folder_id: str = None,
        source_type: SourceType = SourceType.INTERNAL,
        classification: Classification = Classification.INTERNAL,
        description: str = None,
        custom_metadata: Dict = None
    ) -> Document:
        """Create a new document"""
        # Read file content
        file_content = file.read()
        file_size = len(file_content)

        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()

        # Determine mime type
        import magic
        mime_type = magic.from_buffer(file_content, mime=True)

        # Generate file path
        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1]
        stored_filename = f"{doc_id}{file_ext}"
        file_path = os.path.join(self.upload_path, tenant_id, stored_filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Create document record
        document = Document(
            id=doc_id,
            tenant_id=tenant_id,
            title=title,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
            document_type_id=document_type_id,
            department_id=department_id,
            folder_id=folder_id,
            source_type=source_type,
            classification=classification,
            description=description,
            custom_metadata=custom_metadata or {},
            created_by=user_id,
            current_version=1,
            lifecycle_status=LifecycleStatus.DRAFT,
            ocr_status=OCRStatus.PENDING
        )
        self.db.add(document)

        # Create initial version
        version = DocumentVersion(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            version_number=1,
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            created_by=user_id,
            change_summary="Initial version"
        )
        self.db.add(version)

        self.db.commit()
        self.db.refresh(document)
        return document

    def get_document(self, document_id: str, tenant_id: str = None) -> Optional[Document]:
        """Get a document by ID"""
        query = self.db.query(Document).filter(Document.id == document_id)
        if tenant_id:
            query = query.filter(Document.tenant_id == tenant_id)
        return query.first()

    def get_documents(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        folder_id: str = None,
        document_type_id: str = None,
        department_id: str = None,
        lifecycle_status: LifecycleStatus = None,
        source_type: SourceType = None,
        search_query: str = None
    ) -> tuple[List[Document], int]:
        """Get documents with filters"""
        query = self.db.query(Document).filter(Document.tenant_id == tenant_id)

        if folder_id:
            query = query.filter(Document.folder_id == folder_id)
        if document_type_id:
            query = query.filter(Document.document_type_id == document_type_id)
        if department_id:
            query = query.filter(Document.department_id == department_id)
        if lifecycle_status:
            query = query.filter(Document.lifecycle_status == lifecycle_status)
        if source_type:
            query = query.filter(Document.source_type == source_type)
        if search_query:
            query = query.filter(
                or_(
                    Document.title.ilike(f"%{search_query}%"),
                    Document.description.ilike(f"%{search_query}%"),
                    Document.filename.ilike(f"%{search_query}%")
                )
            )

        total = query.count()
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        return documents, total

    def update_document(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        **kwargs
    ) -> Optional[Document]:
        """Update document metadata"""
        document = self.get_document(document_id, tenant_id)
        if not document:
            return None

        allowed_fields = [
            'title', 'description', 'document_type_id', 'department_id',
            'folder_id', 'classification', 'custom_metadata'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(document, field, value)

        document.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: str, tenant_id: str) -> bool:
        """Soft delete a document"""
        document = self.get_document(document_id, tenant_id)
        if not document:
            return False

        # Check if document is under legal hold or WORM locked
        if document.is_worm_locked or document.has_legal_hold:
            raise ValueError("Cannot delete document under legal hold or WORM lock")

        document.is_deleted = True
        document.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def transition_lifecycle(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        new_status: LifecycleStatus
    ) -> Optional[Document]:
        """Transition document lifecycle status"""
        document = self.get_document(document_id, tenant_id)
        if not document:
            return None

        # Validate transition
        valid_transitions = {
            LifecycleStatus.DRAFT: [LifecycleStatus.REVIEW],
            LifecycleStatus.REVIEW: [LifecycleStatus.APPROVED, LifecycleStatus.DRAFT],
            LifecycleStatus.APPROVED: [LifecycleStatus.ARCHIVED],
            LifecycleStatus.ARCHIVED: []
        }

        if new_status not in valid_transitions.get(document.lifecycle_status, []):
            raise ValueError(f"Invalid transition from {document.lifecycle_status} to {new_status}")

        document.lifecycle_status = new_status
        document.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(document)
        return document

    # Version management
    def create_version(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        file: BinaryIO,
        filename: str,
        change_summary: str = None
    ) -> DocumentVersion:
        """Create a new version of a document"""
        document = self.get_document(document_id, tenant_id)
        if not document:
            raise ValueError("Document not found")

        # Check if document is locked by another user
        lock = self.db.query(DocumentLock).filter(
            DocumentLock.document_id == document_id,
            DocumentLock.is_active == True
        ).first()

        if lock and lock.user_id != user_id:
            raise ValueError("Document is locked by another user")

        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        checksum = hashlib.sha256(file_content).hexdigest()

        # Generate new file path
        new_version = document.current_version + 1
        file_ext = os.path.splitext(filename)[1]
        stored_filename = f"{document_id}_v{new_version}{file_ext}"
        file_path = os.path.join(self.upload_path, tenant_id, stored_filename)

        # Save file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Create version record
        version = DocumentVersion(
            id=str(uuid.uuid4()),
            document_id=document_id,
            version_number=new_version,
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            created_by=user_id,
            change_summary=change_summary
        )
        self.db.add(version)

        # Update document
        document.current_version = new_version
        document.file_path = file_path
        document.file_size = file_size
        document.checksum = checksum
        document.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(version)
        return version

    def get_versions(self, document_id: str) -> List[DocumentVersion]:
        """Get all versions of a document"""
        return self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).all()

    # Document locking
    def checkout_document(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str
    ) -> DocumentLock:
        """Check out a document for editing"""
        document = self.get_document(document_id, tenant_id)
        if not document:
            raise ValueError("Document not found")

        # Check for existing lock
        existing_lock = self.db.query(DocumentLock).filter(
            DocumentLock.document_id == document_id,
            DocumentLock.is_active == True
        ).first()

        if existing_lock:
            if existing_lock.user_id == user_id:
                return existing_lock
            raise ValueError("Document is already checked out by another user")

        lock = DocumentLock(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=user_id,
            is_active=True
        )
        self.db.add(lock)
        self.db.commit()
        self.db.refresh(lock)
        return lock

    def checkin_document(
        self,
        document_id: str,
        user_id: str
    ) -> bool:
        """Check in a document"""
        lock = self.db.query(DocumentLock).filter(
            DocumentLock.document_id == document_id,
            DocumentLock.user_id == user_id,
            DocumentLock.is_active == True
        ).first()

        if not lock:
            return False

        lock.is_active = False
        lock.checked_in_at = datetime.utcnow()
        self.db.commit()
        return True

    # Folder management
    def create_folder(
        self,
        tenant_id: str,
        name: str,
        parent_id: str = None,
        path: str = None
    ) -> Folder:
        """Create a folder"""
        if not path:
            if parent_id:
                parent = self.db.query(Folder).filter(Folder.id == parent_id).first()
                path = f"{parent.path}/{name}" if parent else f"/{name}"
            else:
                path = f"/{name}"

        folder = Folder(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            parent_id=parent_id,
            path=path
        )
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def get_folders(
        self,
        tenant_id: str,
        parent_id: str = None
    ) -> List[Folder]:
        """Get folders"""
        query = self.db.query(Folder).filter(Folder.tenant_id == tenant_id)
        if parent_id:
            query = query.filter(Folder.parent_id == parent_id)
        else:
            query = query.filter(Folder.parent_id == None)
        return query.all()

    # Document types
    def get_document_types(self, tenant_id: str) -> List[DocumentType]:
        """Get document types for tenant"""
        return self.db.query(DocumentType).filter(
            DocumentType.tenant_id == tenant_id
        ).all()

    # Departments
    def get_departments(self, tenant_id: str) -> List[Department]:
        """Get departments for tenant"""
        return self.db.query(Department).filter(
            Department.tenant_id == tenant_id
        ).all()
