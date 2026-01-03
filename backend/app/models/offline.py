"""Offline/Edge Capture models for M17 - PWA Support"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Integer,
    Boolean,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    CONFLICT = "conflict"
    FAILED = "failed"


class SyncOperation(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncQueue(Base):
    """Queue for offline changes pending sync"""
    __tablename__ = "sync_queue"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    device_id = Column(String(100), nullable=False)

    # Entity details
    entity_type = Column(String(50), nullable=False)  # document, folder, metadata
    entity_id = Column(String(36), nullable=True)  # null for CREATE
    local_id = Column(String(36), nullable=False)  # client-side ID

    # Operation
    operation = Column(Enum(SyncOperation), nullable=False)
    payload = Column(JSON, default=dict)  # Data to sync

    # Sync status
    status = Column(Enum(SyncStatus), default=SyncStatus.PENDING)
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    conflict_data = Column(JSON, nullable=True)  # Server state for conflict resolution

    # Timestamps
    client_timestamp = Column(DateTime, nullable=False)  # When change was made offline
    created_at = Column(DateTime, default=datetime.utcnow)
    synced_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_sync_queue_status_user", "status", "user_id"),
        Index("ix_sync_queue_device", "device_id"),
    )


class DeviceRegistration(Base):
    """Registered devices for offline sync"""
    __tablename__ = "device_registrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    device_id = Column(String(100), nullable=False, unique=True)
    device_name = Column(String(200), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, tablet, desktop
    os_info = Column(String(100), nullable=True)
    browser_info = Column(String(100), nullable=True)

    # Sync state
    last_sync_at = Column(DateTime, nullable=True)
    sync_version = Column(Integer, default=0)  # Incremental sync version

    # Offline storage quota (MB)
    storage_quota = Column(Integer, default=500)
    storage_used = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_device_registrations_user", "user_id"),
    )


class OfflineDocument(Base):
    """Documents marked for offline availability"""
    __tablename__ = "offline_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    device_id = Column(String(100), nullable=False)

    # Sync status
    is_synced = Column(Boolean, default=False)
    synced_version = Column(Integer, nullable=True)
    synced_at = Column(DateTime, nullable=True)

    # Size tracking
    file_size = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    document = relationship("Document", foreign_keys=[document_id])

    __table_args__ = (
        Index("ix_offline_documents_user_device", "user_id", "device_id"),
        Index("ix_offline_documents_document", "document_id"),
    )


class SyncConflict(Base):
    """Conflict records for manual resolution"""
    __tablename__ = "sync_conflicts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_queue_id = Column(String(36), ForeignKey("sync_queue.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)

    # Conflicting data
    client_data = Column(JSON, nullable=False)
    server_data = Column(JSON, nullable=False)
    client_timestamp = Column(DateTime, nullable=False)
    server_timestamp = Column(DateTime, nullable=False)

    # Resolution
    resolution = Column(String(20), nullable=True)  # client_wins, server_wins, merged
    resolved_data = Column(JSON, nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sync_item = relationship("SyncQueue", foreign_keys=[sync_queue_id])
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    __table_args__ = (
        Index("ix_sync_conflicts_user", "user_id"),
    )
