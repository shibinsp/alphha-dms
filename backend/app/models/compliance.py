"""Compliance Models - M06 WORM, M07 Retention, M08 Legal Hold"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Date, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class RetentionUnit(str, enum.Enum):
    DAYS = "DAYS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


class RetentionAction(str, enum.Enum):
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    REVIEW = "REVIEW"
    EXTEND = "EXTEND"


class LegalHoldStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


# M06 - WORM Records
class WORMRecord(Base):
    """Write-Once-Read-Many locked records"""
    __tablename__ = "worm_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, unique=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Lock information
    locked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    locked_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    lock_reason = Column(Text)

    # Retention settings
    retention_until = Column(DateTime, nullable=False)  # Cannot be unlocked before this
    retention_extended = Column(Boolean, default=False)
    original_retention_until = Column(DateTime)  # If extended, keep original

    # Integrity verification
    content_hash = Column(String(64), nullable=False)  # SHA-256 hash at lock time
    last_verified_at = Column(DateTime)
    last_verified_hash = Column(String(64))
    verification_count = Column(Integer, default=0)

    # Relationships
    document = relationship("Document", backref="worm_record")
    tenant = relationship("Tenant", backref="worm_records")
    locker = relationship("User", backref="worm_locks")


# M07 - Retention Policies
class RetentionPolicy(Base):
    """Document retention policy definitions"""
    __tablename__ = "retention_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # What this policy applies to
    document_type_id = Column(String(36), ForeignKey("document_types.id"), nullable=True)
    source_type = Column(String(20), nullable=True)  # CUSTOMER, VENDOR, INTERNAL
    classification = Column(String(20), nullable=True)  # PUBLIC, INTERNAL, etc.

    # Retention period
    retention_period = Column(Integer, nullable=False)
    retention_unit = Column(Enum(RetentionUnit), nullable=False)

    # Action when retention expires
    expiry_action = Column(Enum(RetentionAction), nullable=False)

    # Notifications
    notify_days_before = Column(Integer, default=30)  # Notify N days before expiry
    notify_roles = Column(JSON)  # Role IDs to notify

    # Auto-apply
    auto_apply = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority policies override

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"))

    # Relationships
    tenant = relationship("Tenant", backref="retention_policies")
    document_type = relationship("DocumentType", backref="retention_policies")
    creator = relationship("User", backref="created_retention_policies")


class PolicyExecutionLog(Base):
    """Log of retention policy executions"""
    __tablename__ = "policy_execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    policy_id = Column(String(36), ForeignKey("retention_policies.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)

    action_taken = Column(Enum(RetentionAction), nullable=False)
    action_status = Column(String(20), nullable=False)  # SUCCESS, FAILED, SKIPPED
    action_result = Column(Text)  # Details or error message

    executed_at = Column(DateTime, default=datetime.utcnow)
    executed_by = Column(String(50))  # "SYSTEM" or user_id

    # Relationships
    tenant = relationship("Tenant", backref="policy_executions")
    policy = relationship("RetentionPolicy", backref="executions")
    document = relationship("Document", backref="policy_executions")


# M08 - Legal Hold
class LegalHold(Base):
    """Legal hold records for e-discovery"""
    __tablename__ = "legal_holds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Hold identification
    hold_name = Column(String(255), nullable=False)
    case_number = Column(String(100))
    matter_name = Column(String(255))
    description = Column(Text)

    # Legal counsel
    legal_counsel = Column(String(255))
    counsel_email = Column(String(255))

    # Hold period
    hold_start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    hold_end_date = Column(DateTime, nullable=True)
    status = Column(Enum(LegalHoldStatus), default=LegalHoldStatus.ACTIVE, nullable=False)

    # Scope - which documents are covered
    scope_criteria = Column(JSON)  # Search criteria to identify documents
    # Example: {"date_from": "2024-01-01", "date_to": "2024-06-30", "keywords": ["contract"]}

    # Statistics
    documents_held = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    released_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    released_at = Column(DateTime, nullable=True)
    release_reason = Column(Text)

    # Relationships
    tenant = relationship("Tenant", backref="legal_holds")
    creator = relationship("User", foreign_keys=[created_by])
    releaser = relationship("User", foreign_keys=[released_by])
    documents = relationship("LegalHoldDocument", back_populates="legal_hold", cascade="all, delete-orphan")


class LegalHoldDocument(Base):
    """Documents under legal hold"""
    __tablename__ = "legal_hold_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    legal_hold_id = Column(String(36), ForeignKey("legal_holds.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)

    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Snapshot at time of hold
    snapshot_metadata = Column(JSON)  # Document metadata at time of hold

    # Relationships
    legal_hold = relationship("LegalHold", back_populates="documents")
    document = relationship("Document", backref="legal_hold_entries")
    adder = relationship("User", backref="added_legal_hold_docs")


class EvidenceExport(Base):
    """E-discovery export records"""
    __tablename__ = "evidence_exports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_hold_id = Column(String(36), ForeignKey("legal_holds.id"), nullable=False)

    # Export details
    export_name = Column(String(255), nullable=False)
    export_format = Column(String(50), nullable=False)  # ZIP, PST, PDF_PORTFOLIO
    export_path = Column(String(500))

    # Manifest
    manifest = Column(JSON)  # List of exported documents with checksums
    document_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)

    # Chain of custody
    exported_at = Column(DateTime, default=datetime.utcnow)
    exported_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    export_hash = Column(String(64))  # SHA-256 of entire export

    # Delivery tracking
    delivered_to = Column(String(255))
    delivered_at = Column(DateTime)
    delivery_method = Column(String(50))  # EMAIL, DOWNLOAD, PHYSICAL

    # Relationships
    tenant = relationship("Tenant", backref="evidence_exports")
    legal_hold = relationship("LegalHold", backref="exports")
    exporter = relationship("User", backref="evidence_exports")
