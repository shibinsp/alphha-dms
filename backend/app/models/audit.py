import uuid
from datetime import datetime, date
import enum

from sqlalchemy import Column, String, BigInteger, DateTime, Date, ForeignKey, Text, JSON, Enum, Integer

from sqlalchemy.orm import relationship

from app.core.database import Base


class VerificationResult(str, enum.Enum):
    """Audit verification result."""
    PASSED = "PASSED"
    FAILED = "FAILED"


class AuditEvent(Base):
    """Immutable audit event log with hash chaining."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sequence_number = Column(BigInteger, autoincrement=True, unique=True, nullable=False)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # document, user, role, etc.
    entity_id = Column(String(36), nullable=False, index=True)

    # Actor
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Change details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    event_metadata = Column(JSON, nullable=True)

    # Hash chain for integrity
    event_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=False)

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AuditEvent {self.event_type} {self.entity_type}/{self.entity_id}>"


class AuditRoot(Base):
    """Daily Merkle root for audit integrity verification."""
    __tablename__ = "audit_roots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(Date, nullable=False, index=True)
    merkle_root = Column(String(64), nullable=False)
    event_count = Column(Integer, nullable=False)
    first_sequence = Column(BigInteger, nullable=False)
    last_sequence = Column(BigInteger, nullable=False)

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditRoot {self.date} ({self.event_count} events)>"


class AuditVerification(Base):
    """Audit verification records."""
    __tablename__ = "audit_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Verification scope
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    date_range_start = Column(Date, nullable=False)
    date_range_end = Column(Date, nullable=False)

    # Results
    result = Column(Enum(VerificationResult), nullable=False)
    details = Column(JSON, nullable=True)  # Detailed verification results

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    verifier = relationship("User")

    def __repr__(self):
        return f"<AuditVerification {self.date_range_start} to {self.date_range_end}: {self.result}>"


# Event types for audit logging
AUDIT_EVENT_TYPES = {
    # Authentication
    "auth.login": "User logged in",
    "auth.logout": "User logged out",
    "auth.login_failed": "Failed login attempt",
    "auth.mfa_enabled": "MFA enabled",
    "auth.mfa_disabled": "MFA disabled",
    "auth.password_changed": "Password changed",
    "auth.password_reset": "Password reset requested",

    # User management
    "user.created": "User created",
    "user.updated": "User updated",
    "user.deactivated": "User deactivated",
    "user.activated": "User activated",
    "user.role_assigned": "Role assigned to user",
    "user.role_removed": "Role removed from user",

    # Document lifecycle
    "document.created": "Document created",
    "document.updated": "Document metadata updated",
    "document.deleted": "Document deleted",
    "document.viewed": "Document viewed",
    "document.downloaded": "Document downloaded",
    "document.shared": "Document shared",
    "document.unshared": "Document sharing revoked",

    # Document versions
    "document.version_created": "New version created",
    "document.version_restored": "Version restored",
    "document.checked_out": "Document checked out",
    "document.checked_in": "Document checked in",

    # Lifecycle transitions
    "document.submitted_for_review": "Submitted for review",
    "document.approved": "Document approved",
    "document.rejected": "Document rejected",
    "document.archived": "Document archived",

    # Compliance
    "document.worm_locked": "WORM lock applied",
    "document.legal_hold_applied": "Legal hold applied",
    "document.legal_hold_released": "Legal hold released",

    # PII
    "pii.detected": "PII detected in document",
    "pii.viewed_unmasked": "Unmasked PII viewed",
    "pii.exported": "PII data exported",

    # Admin
    "role.created": "Role created",
    "role.updated": "Role updated",
    "role.deleted": "Role deleted",
    "tenant.created": "Tenant created",
    "tenant.updated": "Tenant updated",
    "policy.created": "Policy created",
    "policy.updated": "Policy updated",
    "policy.executed": "Policy executed",
}
