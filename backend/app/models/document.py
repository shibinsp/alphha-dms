import uuid
from datetime import datetime
import enum

from sqlalchemy import (
    Column, String, BigInteger, Integer, DateTime,
    ForeignKey, Text, Boolean, JSON, Index, Enum
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class SourceType(str, enum.Enum):
    """Document source classification."""
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    INTERNAL = "INTERNAL"


class Classification(str, enum.Enum):
    """Document security classification."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class LifecycleStatus(str, enum.Enum):
    """Document lifecycle states."""
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class OCRStatus(str, enum.Enum):
    """OCR processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApprovalFlowType(str, enum.Enum):
    """Approval flow configuration."""
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    NONE = "NONE"


class FieldType(str, enum.Enum):
    """Custom field types."""
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    BOOLEAN = "BOOLEAN"


class Document(Base):
    """Core document model."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable=True)
    checksum_sha256 = Column(String(64), nullable=False)

    # Source classification
    source_type = Column(Enum(SourceType), nullable=False)
    customer_id = Column(String(100), nullable=True, index=True)
    vendor_id = Column(String(100), nullable=True, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)

    # Document categorization
    document_type_id = Column(String(36), ForeignKey("document_types.id"), nullable=False)
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=True)

    # Security & Compliance
    classification = Column(Enum(Classification), default=Classification.INTERNAL)
    lifecycle_status = Column(Enum(LifecycleStatus), default=LifecycleStatus.DRAFT)

    # WORM & Retention
    is_worm_locked = Column(Boolean, default=False)
    retention_expiry = Column(DateTime, nullable=True)

    # Legal Hold
    legal_hold = Column(Boolean, default=False)
    legal_hold_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    legal_hold_at = Column(DateTime, nullable=True)

    # Versioning
    current_version_id = Column(String(36), nullable=True)

    # OCR
    ocr_text = Column(Text, nullable=True)
    ocr_status = Column(Enum(OCRStatus), default=OCRStatus.PENDING)
    ocr_confidence = Column(Integer, nullable=True)  # 0-100

    # AI-extracted metadata (from Mistral)
    extracted_metadata = Column(JSON, default={})

    # Custom metadata
    custom_metadata = Column(JSON, default={})

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Audit
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_documents_tenant_status", "tenant_id", "lifecycle_status"),
        Index("idx_documents_type", "document_type_id"),
        Index("idx_documents_created", "created_at"),
        Index("idx_documents_source", "source_type", "tenant_id"),
    )

    # Relationships
    document_type = relationship("DocumentType", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")
    department = relationship("Department", back_populates="documents")
    tenant = relationship("Tenant", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    legal_hold_user = relationship("User", foreign_keys=[legal_hold_by])

    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentType(Base):
    """Document type classification."""
    __tablename__ = "document_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon name for UI

    # Retention settings
    retention_days = Column(Integer, nullable=True)

    # Approval settings
    approval_flow_type = Column(Enum(ApprovalFlowType), default=ApprovalFlowType.NONE)
    auto_approvers = Column(JSON, nullable=True)  # List of user IDs or role names

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="document_types")
    documents = relationship("Document", back_populates="document_type")
    custom_fields = relationship("CustomField", back_populates="document_type")

    def __repr__(self):
        return f"<DocumentType {self.name}>"


class Folder(Base):
    """Hierarchical folder structure."""
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    parent_id = Column(String(36), ForeignKey("folders.id"), nullable=True)
    path = Column(String(1000), nullable=False)  # Full path like "/root/subfolder"

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], backref="children")
    documents = relationship("Document", back_populates="folder")

    def __repr__(self):
        return f"<Folder {self.path}>"


class Department(Base):
    """Department definition for internal documents."""
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="departments")
    documents = relationship("Document", back_populates="department")

    def __repr__(self):
        return f"<Department {self.name}>"


class CustomField(Base):
    """User-definable metadata fields."""
    __tablename__ = "custom_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    field_key = Column(String(100), nullable=False)  # Key for JSON storage
    field_type = Column(Enum(FieldType), nullable=False)
    options = Column(JSON, nullable=True)  # For SELECT/MULTI_SELECT types
    required = Column(Boolean, default=False)
    default_value = Column(String(500), nullable=True)

    # Associated document type (null for global fields)
    document_type_id = Column(String(36), ForeignKey("document_types.id"), nullable=True)

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document_type = relationship("DocumentType", back_populates="custom_fields")

    def __repr__(self):
        return f"<CustomField {self.name}>"
