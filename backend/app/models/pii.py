"""PII Detection and DLP Models - M09"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON, LargeBinary, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class PIIType(str, enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    AADHAAR = "AADHAAR"  # Indian national ID
    PAN = "PAN"  # Indian tax ID
    SSN = "SSN"  # US Social Security
    IBAN = "IBAN"  # Bank account
    PASSPORT = "PASSPORT"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    CUSTOM = "CUSTOM"


class PIIAction(str, enum.Enum):
    MASK = "MASK"  # Show partial (e.g., ****1234)
    REDACT = "REDACT"  # Replace with [REDACTED]
    ENCRYPT = "ENCRYPT"  # Encrypt in storage
    LOG_ONLY = "LOG_ONLY"  # Just log, no action
    BLOCK = "BLOCK"  # Block document upload


class PIIPattern(Base):
    """PII detection pattern definition"""
    __tablename__ = "pii_patterns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    pii_type = Column(Enum(PIIType), nullable=False)
    description = Column(Text)

    # Detection pattern
    regex_pattern = Column(Text, nullable=False)
    validator_function = Column(String(100))  # e.g., "luhn_check" for credit cards

    # Masking configuration
    mask_format = Column(String(100))  # e.g., "****{last4}"
    mask_char = Column(String(1), default="*")

    # Sensitivity
    sensitivity_level = Column(String(20), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL

    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System patterns can't be deleted

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="pii_patterns")


class PIIPolicy(Base):
    """PII handling policy"""
    __tablename__ = "pii_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Which PII types this policy applies to
    pii_types = Column(JSON)  # List of PIIType values

    # Which document types this applies to
    document_type_ids = Column(JSON)  # List of document type IDs, or null for all

    # Action to take
    action = Column(Enum(PIIAction), nullable=False)

    # Role-based exceptions - who can see unmasked data
    exception_role_ids = Column(JSON)  # List of role IDs that bypass masking

    # Notifications
    notify_on_detection = Column(Boolean, default=True)
    notify_roles = Column(JSON)  # Role IDs to notify

    priority = Column(Integer, default=0)  # Higher priority policies are applied first
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="pii_policies")


class DocumentPIIField(Base):
    """Detected PII in a document"""
    __tablename__ = "document_pii_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    pattern_id = Column(String(36), ForeignKey("pii_patterns.id"), nullable=True)

    pii_type = Column(Enum(PIIType), nullable=False)
    field_name = Column(String(255))  # Where it was found (e.g., "page_3_paragraph_2")

    # Location in document
    page_number = Column(Integer)
    position_start = Column(Integer)
    position_end = Column(Integer)

    # Encrypted original value
    encrypted_value = Column(LargeBinary)  # AES-256 encrypted
    masked_value = Column(String(500))  # For display

    # Confidence of detection
    confidence_score = Column(String(10))  # 0.0 to 1.0

    # Action taken
    action_taken = Column(Enum(PIIAction))

    detected_at = Column(DateTime, default=datetime.utcnow)
    detected_by = Column(String(50))  # "AUTO" or user_id for manual

    # Relationships
    document = relationship("Document", backref="pii_fields")
    pattern = relationship("PIIPattern", backref="detections")


class PIIAccessLog(Base):
    """Audit log for PII access"""
    __tablename__ = "pii_access_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    pii_field_id = Column(String(36), ForeignKey("document_pii_fields.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)

    # Who accessed
    accessed_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    # What they saw
    access_type = Column(String(50))  # "VIEW_MASKED", "VIEW_UNMASKED", "EXPORT"
    saw_unmasked = Column(Boolean, default=False)

    # Context
    reason = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    accessed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="pii_access_logs")
    pii_field = relationship("DocumentPIIField", backref="access_logs")
    document = relationship("Document", backref="pii_access_logs")
    user = relationship("User", backref="pii_access_logs")
