import uuid
from datetime import datetime

from sqlalchemy import Column, String, BigInteger, Integer, DateTime, ForeignKey, Text, Boolean, JSON

from sqlalchemy.orm import relationship

from app.core.database import Base


class DocumentVersion(Base):
    """Document version history. All versions are IMMUTABLE once created - only the current version's document can be edited."""
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # File information
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)

    # Snapshot of metadata at version creation
    metadata_snapshot = Column(JSON, default={})

    # Version notes
    change_reason = Column(Text, nullable=True)

    # Current version indicator
    is_current = Column(Boolean, default=False)

    # Audit
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="versions")
    creator = relationship("User")

    def __repr__(self):
        return f"<DocumentVersion {self.document_id} v{self.version_number}>"


class DocumentLock(Base):
    """Document check-out/check-in lock."""
    __tablename__ = "document_locks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Lock holder
    locked_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    locked_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document")
    user = relationship("User")

    def __repr__(self):
        return f"<DocumentLock {self.document_id}>"
