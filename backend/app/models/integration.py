"""Integration Models - API Keys, Webhooks, External Systems"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class IntegrationType(enum.Enum):
    SIEM = "SIEM"
    IAM = "IAM"
    BANK = "BANK"
    ERP = "ERP"
    CUSTOM = "CUSTOM"


class APIKey(Base):
    """API Keys for external system integration."""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(64), nullable=False)  # SHA256 hash
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    scopes = Column(JSON, default=[])  # ["documents:read", "audit:read"]
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant")
    creator = relationship("User")


class Webhook(Base):
    """Webhooks for event notifications to external systems."""
    __tablename__ = "webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(64), nullable=True)  # For HMAC signing
    events = Column(JSON, default=[])  # ["document.created", "document.approved"]
    is_active = Column(Boolean, default=True)
    headers = Column(JSON, default={})  # Custom headers
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant")


class ExternalIntegration(Base):
    """External system integrations (SIEM, IAM, Banks)."""
    __tablename__ = "external_integrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(SQLEnum(IntegrationType), nullable=False)
    config = Column(JSON, default={})  # Connection config (encrypted in production)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant")
