"""Document Sharing & Permissions Models - M10"""
import uuid
import enum
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class PermissionLevel(str, enum.Enum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
    COMMENTER = "COMMENTER"
    DOWNLOADER = "DOWNLOADER"


class ShareLinkType(str, enum.Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EDIT = "EDIT"


class DocumentPermission(Base):
    """Document permission grants"""
    __tablename__ = "document_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Grant target (one of these)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)

    # Permission level
    permission_level = Column(Enum(PermissionLevel), nullable=False)

    # Inheritance
    inherited_from_folder = Column(String(36), ForeignKey("folders.id"), nullable=True)
    is_inherited = Column(Boolean, default=False)

    # Metadata
    granted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Relationships
    document = relationship("Document", backref="permissions")
    tenant = relationship("Tenant", backref="document_permissions")
    user = relationship("User", foreign_keys=[user_id], backref="document_permissions")
    role = relationship("Role", foreign_keys=[role_id])
    department = relationship("Department", foreign_keys=[department_id])
    granter = relationship("User", foreign_keys=[granted_by])
    revoker = relationship("User", foreign_keys=[revoked_by])


class ShareLink(Base):
    """External share links"""
    __tablename__ = "share_links"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Link details
    token = Column(String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    link_type = Column(Enum(ShareLinkType), default=ShareLinkType.VIEW, nullable=False)

    # Security
    password_hash = Column(String(255), nullable=True)  # Optional password protection
    max_downloads = Column(Integer, nullable=True)  # Null = unlimited
    download_count = Column(Integer, default=0)

    # Validity
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Tracking
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Relationships
    document = relationship("Document", backref="share_links")
    tenant = relationship("Tenant", backref="share_links")
    creator = relationship("User", backref="created_share_links")


class ShareLinkAccess(Base):
    """Share link access log"""
    __tablename__ = "share_link_accesses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_link_id = Column(String(36), ForeignKey("share_links.id"), nullable=False)

    # Access details
    accessed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    action = Column(String(50))  # VIEW, DOWNLOAD

    # Relationships
    share_link = relationship("ShareLink", backref="accesses")
