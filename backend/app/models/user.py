import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    ForeignKey, JSON, Table, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# Association table for User-Role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)

    # Profile
    department = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    clearance_level = Column(String(50), default="PUBLIC")
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)

    # Login tracking
    last_login = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        for role in self.roles:
            if role.permissions and permission in role.permissions:
                return True
        return False

    def get_all_permissions(self) -> set:
        """Get all permissions from all roles."""
        permissions = set()
        for role in self.roles:
            if role.permissions:
                permissions.update(role.permissions)
        return permissions


class Role(Base):
    """Role definition for RBAC."""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, default=[])
    is_system_role = Column(Boolean, default=False)

    # Tenant (null for system-wide roles)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"


# Alias for clarity in imports
UserRole = user_roles


class Session(Base):
    """User session tracking."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.id}>"

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at


# Predefined system permissions
SYSTEM_PERMISSIONS = [
    # Document permissions
    "document.view",
    "document.download",
    "document.upload",
    "document.edit",
    "document.delete",
    "document.share",
    "document.approve",
    "document.legal_hold",

    # Workflow permissions
    "workflow.create",
    "workflow.approve",
    "workflow.manage",

    # Admin permissions
    "admin.users",
    "admin.roles",
    "admin.policies",
    "admin.tenants",

    # Report permissions
    "reports.view",
    "reports.export",

    # Audit permissions
    "audit.view",
    "audit.export",
    "audit.verify",

    # PII permissions
    "pii.unmask",
    "pii.export",
]

# Predefined system roles
SYSTEM_ROLES = {
    "Super Admin": SYSTEM_PERMISSIONS,
    "Admin": [
        "document.view", "document.download", "document.upload", "document.edit",
        "document.delete", "document.share", "document.approve",
        "workflow.create", "workflow.approve", "workflow.manage",
        "admin.users", "admin.roles",
        "reports.view", "reports.export",
        "audit.view"
    ],
    "Legal": [
        "document.view", "document.download",
        "document.legal_hold",
        "audit.view", "audit.export"
    ],
    "Compliance": [
        "document.view", "document.download",
        "audit.view", "audit.export", "audit.verify",
        "reports.view", "reports.export",
        "pii.unmask"
    ],
    "Auditor": [
        "document.view",
        "audit.view", "audit.export", "audit.verify",
        "reports.view"
    ],
    "Manager": [
        "document.view", "document.download", "document.upload", "document.edit",
        "document.share", "document.approve",
        "workflow.create", "workflow.approve",
        "reports.view"
    ],
    "User": [
        "document.view", "document.download", "document.upload", "document.edit",
        "document.share"
    ],
    "Viewer": [
        "document.view", "document.download"
    ]
}
